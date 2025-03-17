from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import (
    select,
    update,
    insert,
    delete,
)
from db_config import engine
from auth_utils import (
    SALT, 
    validate_admin_user, 
    validate_email, 
    validate_password_strength,
    get_hashed_password,
    get_hashed_username
)
from db_models import Users, UserType, UserStatus
import hashlib
import pandas as pd
from io import StringIO
import requests
import asyncio
from fastapi.responses import JSONResponse
import os
from datetime import datetime
from typing import List, Optional

from request_models import (
    DeleteUserRequest,
    AddUserRequest, 
    AddUsersBatchRequest,
    UpdateUserStatusRequest,
    ResetPasswordRequest,
    UserRequest
)
from utils_logging import LOGGER

router = APIRouter()

# Standard error responses
UNAUTHORIZED_RESPONSE = JSONResponse(
    status_code=401,
    content={
        "error": "unauthorized",
        "message": "You are not authorized to perform this action",
    },
)

ADMIN_REQUIRED_RESPONSE = JSONResponse(
    status_code=403,
    content={
        "error": "forbidden",
        "message": "Admin privileges required for this action",
    },
)

VALIDATION_ERROR_RESPONSE = lambda detail: JSONResponse(
    status_code=400,
    content={
        "error": "validation_error",
        "message": "Input validation failed",
        "detail": detail,
    },
)

USER_NOT_FOUND_RESPONSE = JSONResponse(
    status_code=404,
    content={
        "error": "not_found",
        "message": "User not found",
    },
)


async def validate_admin_privileges(token: str) -> bool:
    """Validate that the user has admin privileges."""
    if not token:
        return False
    return await validate_admin_user(token)


@router.post("/admin/add_user")
async def add_single_user(request: AddUserRequest):
    """
    Add a single user to the system.
    """
    # Validate admin privileges
    if not await validate_admin_privileges(request.token):
        return ADMIN_REQUIRED_RESPONSE
    
    # Validate email format
    is_valid_email, email_error = validate_email(request.user.username)
    if not is_valid_email:
        return VALIDATION_ERROR_RESPONSE(email_error)
    
    # Validate password if provided
    if request.user.password:
        is_valid_password, password_error = validate_password_strength(request.user.password)
        if not is_valid_password:
            return VALIDATION_ERROR_RESPONSE(password_error)
    
    # Process user creation
    async with engine.begin() as conn:
        # Check if user already exists
        user_exists = await conn.execute(
            select(Users).where(Users.username == request.user.username)
        )
        user_exists = user_exists.fetchone()
        
        # Hash the password
        if request.user.password:
            hashed_password = get_hashed_password(request.user.username, request.user.password)
        else:
            hashed_password = get_hashed_username(request.user.username)
        
        # Determine user type
        user_type = UserType.ADMIN if request.user.user_type == "ADMIN" else UserType.GENERAL
        
        if user_exists:
            # Update existing user
            await conn.execute(
                update(Users)
                .where(Users.username == request.user.username)
                .values(
                    hashed_password=hashed_password,
                    token=hashed_password,
                    user_type=user_type,
                    status=UserStatus.ACTIVE
                )
            )
        else:
            # Create new user
            await conn.execute(
                insert(Users).values(
                    username=request.user.username,
                    hashed_password=hashed_password,
                    token=hashed_password,
                    user_type=user_type,
                    status=UserStatus.ACTIVE,
                    created_at=datetime.now()
                )
            )
    
    return {"status": "success", "message": "User added successfully"}


@router.post("/admin/add_users")
async def add_users_batch(request: AddUsersBatchRequest):
    """
    Add multiple users via CSV upload or Google Sheets URL.
    """
    # Validate admin privileges
    if not await validate_admin_privileges(request.token):
        return ADMIN_REQUIRED_RESPONSE
    
    if not request.gsheets_url and not request.users_csv:
        return VALIDATION_ERROR_RESPONSE("No user details, CSV, or Google Sheet URL provided")
    
    # Get users from Google Sheets if URL provided
    if request.gsheets_url:
        try:
            url_to_query = (
                request.gsheets_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv&sheet=v4"
            )
            user_dets_csv = await asyncio.to_thread(requests.get, url_to_query)
            request.users_csv = user_dets_csv.text
        except Exception as e:
            LOGGER.error(f"Error fetching Google Sheet: {str(e)}")
            return VALIDATION_ERROR_RESPONSE("Could not retrieve data from Google Sheet")
    
    # Parse CSV data
    try:
        users_df = pd.read_csv(StringIO(request.users_csv)).fillna("")
        users = users_df.to_dict(orient="records")
    except Exception as e:
        LOGGER.error(f"Error parsing CSV: {str(e)}")
        return VALIDATION_ERROR_RESPONSE("Could not parse CSV data. Please ensure it's a valid CSV file.")
    
    # Process users
    processed_users = []
    errors = []
    
    for index, user in enumerate(users):
        username = user.get("username", user.get("user_email", "")).lower()
        password = user.get("password", user.get("user_password", ""))
        user_type_str = user.get("user_type", "GENERAL").upper()
        
        # Validate email
        is_valid_email, email_error = validate_email(username)
        if not is_valid_email:
            errors.append(f"Row {index+1}: {email_error}")
            continue
        
        # Validate password if provided
        if password and len(password) > 0:
            is_valid_password, password_error = validate_password_strength(password)
            if not is_valid_password:
                errors.append(f"Row {index+1} ({username}): {password_error}")
                continue
        
        # Determine user type
        user_type = UserType.ADMIN if user_type_str == "ADMIN" else UserType.GENERAL
        
        processed_users.append({
            "username": username,
            "password": password,
            "user_type": user_type
        })
    
    # If there are validation errors, return them
    if errors:
        return VALIDATION_ERROR_RESPONSE(errors)
    
    # Save users to database
    async with engine.begin() as conn:
        for user in processed_users:
            if user["password"]:
                hashed_password = get_hashed_password(user["username"], user["password"])
            else:
                hashed_password = get_hashed_username(user["username"])
            
            # Check if user exists
            user_exists = await conn.execute(
                select(Users).where(Users.username == user["username"])
            )
            user_exists = user_exists.fetchone()
            
            if user_exists:
                # Update existing user
                await conn.execute(
                    update(Users)
                    .where(Users.username == user["username"])
                    .values(
                        hashed_password=hashed_password,
                        token=hashed_password,
                        user_type=user["user_type"],
                        status=UserStatus.ACTIVE
                    )
                )
            else:
                # Create new user
                await conn.execute(
                    insert(Users).values(
                        username=user["username"],
                        hashed_password=hashed_password,
                        token=hashed_password,
                        user_type=user["user_type"],
                        status=UserStatus.ACTIVE,
                        created_at=datetime.now()
                    )
                )
    
    return {
        "status": "success", 
        "message": f"Added/Updated {len(processed_users)} users successfully"
    }


@router.post("/admin/get_users")
async def get_users(request: UserRequest):
    """
    Get all users in the system.
    """
    # Validate admin privileges
    if not await validate_admin_privileges(request.token):
        return ADMIN_REQUIRED_RESPONSE
    
    # Retrieve users from database
    async with engine.begin() as conn:
        result = await conn.execute(select(Users))
        users = result.fetchall()
    
    # Convert to dictionary format
    users_list = []
    for user in users:
        user_dict = {
            "username": user.username,
            "user_type": user.user_type.value if hasattr(user, 'user_type') and user.user_type else "ADMIN",
            "status": user.status.value if hasattr(user, 'status') and user.status else "ACTIVE",
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "allowed_dbs": ""  # Maintained for backward compatibility
        }
        users_list.append(user_dict)
    
    return {"users": users_list}


@router.post("/admin/update_user_status")
async def update_user_status(request: UpdateUserStatusRequest):
    """
    Update a user's status (active/inactive).
    """
    # Validate admin privileges
    if not await validate_admin_privileges(request.token):
        return ADMIN_REQUIRED_RESPONSE
    
    # Convert status string to enum value
    status = UserStatus.ACTIVE if request.status == "ACTIVE" else UserStatus.INACTIVE
    
    # Update user status
    async with engine.begin() as conn:
        # Check if user exists
        user_exists = await conn.execute(
            select(Users).where(Users.username == request.username)
        )
        user_exists = user_exists.fetchone()
        
        if not user_exists:
            return USER_NOT_FOUND_RESPONSE
        
        # Update user status
        await conn.execute(
            update(Users)
            .where(Users.username == request.username)
            .values(status=status)
        )
    
    return {
        "status": "success", 
        "message": f"User status updated to {request.status}"
    }


@router.post("/admin/delete_user")
async def delete_user(request: DeleteUserRequest):
    """
    Delete a user from the system.
    """
    # Validate admin privileges
    if not await validate_admin_privileges(request.token):
        return ADMIN_REQUIRED_RESPONSE
    
    # Delete user
    async with engine.begin() as conn:
        # Check if user exists
        user_exists = await conn.execute(
            select(Users).where(Users.username == request.username)
        )
        user_exists = user_exists.fetchone()
        
        if not user_exists:
            return USER_NOT_FOUND_RESPONSE
        
        # Delete user
        await conn.execute(
            delete(Users).where(Users.username == request.username)
        )
    
    return {"status": "success", "message": "User deleted successfully"}


@router.post("/admin/reset_password")
async def admin_reset_password(request: ResetPasswordRequest):
    """
    Reset a user's password (admin function).
    """
    # Validate admin privileges
    if not await validate_admin_privileges(request.token):
        return ADMIN_REQUIRED_RESPONSE
    
    # Validate password
    is_valid_password, password_error = validate_password_strength(request.password)
    if not is_valid_password:
        return VALIDATION_ERROR_RESPONSE(password_error)
    
    # Reset password
    async with engine.begin() as conn:
        # Check if user exists
        user_exists = await conn.execute(
            select(Users).where(Users.username == request.username)
        )
        user_exists = user_exists.fetchone()
        
        if not user_exists:
            return USER_NOT_FOUND_RESPONSE
        
        # Update password
        hashed_password = get_hashed_password(request.username, request.password)
        await conn.execute(
            update(Users)
            .where(Users.username == request.username)
            .values(
                hashed_password=hashed_password,
                token=hashed_password
            )
        )
    
    return {"status": "success", "message": "Password reset successfully"}


@router.post("/get_non_admin_config")
async def get_non_admin_config():
    """
    Get configuration settings for non-admin users.
    """
    # Get environment variables
    hide_sql_tab = os.getenv("HIDE_SQL_TAB_FOR_NON_ADMIN")
    hide_preview_tabs = os.getenv("HIDE_PREVIEW_TABS_FOR_NON_ADMIN")
    hidden_charts = os.getenv("HIDDEN_CHARTS_FOR_NON_ADMIN")
    hide_raw_analysis = os.getenv("HIDE_RAW_ANALYSIS_FOR_NON_ADMIN")
    
    # Process hidden charts list
    parsed_hidden_charts = None
    if hidden_charts:
        parsed_hidden_charts = [x.strip().lower() for x in hidden_charts.split(",")]
    
    return {
        "hide_sql_tab_for_non_admin": hide_sql_tab in ("yes", "true"),
        "hide_preview_tabs_for_non_admin": hide_preview_tabs in ("yes", "true"),
        "hidden_charts_for_non_admin": parsed_hidden_charts,
        "hide_raw_analysis_for_non_admin": hide_raw_analysis in ("yes", "true"),
    }


@router.post("/admin/add_user_with_token")
async def add_user_with_token(request: Request):
    """
    Add a user with an existing token (for SSO integration).
    """
    params = await request.json()
    auth_token = params.get("auth_token")
    user_token = params.get("user_token")
    username = params.get("username")
    user_type_str = params.get("user_type", "GENERAL")
    
    # Validate admin privileges
    if not await validate_admin_privileges(auth_token):
        return ADMIN_REQUIRED_RESPONSE
    
    # Validate email
    is_valid_email, email_error = validate_email(username)
    if not is_valid_email:
        return VALIDATION_ERROR_RESPONSE(email_error)
    
    # Determine user type
    user_type = UserType.ADMIN if user_type_str.upper() == "ADMIN" else UserType.GENERAL
    
    # Add/update user
    async with engine.begin() as conn:
        # Check if user exists
        user_exists = await conn.execute(
            select(Users).where(Users.username == username)
        )
        user_exists = user_exists.fetchone()
        
        if user_exists:
            # Update existing user
            await conn.execute(
                update(Users)
                .where(Users.username == username)
                .values(
                    hashed_password=user_token,
                    token=user_token,
                    user_type=user_type,
                    status=UserStatus.ACTIVE
                )
            )
        else:
            # Create new user
            await conn.execute(
                insert(Users).values(
                    username=username,
                    hashed_password=user_token,
                    token=user_token,
                    user_type=user_type,
                    status=UserStatus.ACTIVE,
                    created_at=datetime.now()
                )
            )
    
    return {"status": "success", "message": "User added/updated successfully"}
