from fastapi import APIRouter, Request, HTTPException
from auth_utils import login_user, reset_password, get_hashed_username, validate_user
from google.oauth2 import id_token
from google.auth.transport import requests
import asyncio
import os
from fastapi.responses import JSONResponse
from datetime import datetime
from sqlalchemy import and_

from db_models import Users
from request_models import LoginRequest
from utils_logging import LOGGER

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

router = APIRouter()


@router.post("/login")
async def login(req: LoginRequest):
    """
    Login endpoint for password-based authentication.
    
    Args:
        req: LoginRequest containing username and password
        
    Returns:
        User authentication details on success, or error on failure
    """
    from db_config import engine
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    
    # Use a single session for both operations
    async with AsyncSession(engine) as session:
        if req.password:
            from auth_utils import get_hashed_password
            hashed_password = get_hashed_password(req.username, req.password)
        else:
            from auth_utils import get_hashed_username
            hashed_password = get_hashed_username(req.username)
        
        # Query the user
        result = await session.execute(
            select(Users).where(
                and_(
                    Users.hashed_password == hashed_password,
                    Users.username == req.username,
                    Users.status == "ACTIVE",  # Only allow active users to log in
                )
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            token = user.token
            user_type = user.user_type.value if hasattr(user, 'user_type') and user.user_type else "ADMIN"
            username = user.username
            last_login = datetime.now()
            # Update last login timestamp
            user.last_login = last_login
            await session.commit()
            
            return {
                "status": "success",
                "token": token,
                "user_type": user_type,
                "username": username,
                "last_login": last_login.isoformat()
            }
    
    # If we get here, authentication failed
    return JSONResponse(
        status_code=401,
        content={
            "error": "unauthorized",
            "message": "Invalid username or password",
        },
    )


@router.post("/get_google_client_id")
async def get_google_client_id(request: Request):
    if GOOGLE_CLIENT_ID is None or GOOGLE_CLIENT_ID == "":
        return JSONResponse(
            content={"error": "Google client ID not set"}, status_code=400
        )
    return {"google_client_id": GOOGLE_CLIENT_ID}


async def validate_google_token(token: str):
    """
    Validate Google OAuth token and authenticate user.
    
    Args:
        token: Google OAuth ID token
        
    Returns:
        User authentication details on success, or error on failure
    """
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = await asyncio.to_thread(
            id_token.verify_oauth2_token, token, requests.Request(), GOOGLE_CLIENT_ID
        )

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        user_email = idinfo.get("email")
        hashed_password = get_hashed_username(user_email)
        LOGGER.info(f"user_email: {user_email}, hashed_password: {hashed_password}")

        # Handle all database operations in a single session
        from db_config import engine
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with AsyncSession(engine) as session:
            # First check if user exists by token
            result = await session.execute(
                select(Users).where(Users.token == hashed_password)
            )
            user_exists = result.scalar_one_or_none()
            
            if not user_exists:
                return {
                    "error": "user_not_registered",
                    "message": "User is not registered with the system. Please contact the administrator."
                }
            
            # Get active user by username
            result = await session.execute(
                select(Users).where(
                    and_(
                        Users.username == user_email,
                        Users.status == "ACTIVE"
                    )
                )
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update last login timestamp
                import datetime
                user.last_login = datetime.datetime.now()
                await session.commit()
                
                return {
                    "status": "success",
                    "token": user.token,
                    "user_type": user.user_type.value if hasattr(user, 'user_type') and user.user_type else "ADMIN",
                    "username": user.username,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
        
        # If we get here, authentication failed
        return {
            "error": "authentication_failed",
            "message": "Authentication failed. Please try again."
        }
        
    except ValueError as e:
        LOGGER.error(f"Google token validation error: {str(e)}")
        # Invalid token
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid Google authentication token",
            },
        )


@router.post("/login_google")
async def login_google(request: Request):
    body = await request.json()
    token = body.get("credential")
    if not token:
        raise HTTPException(status_code=400, detail="Missing Google ID token.")
    return await validate_google_token(token)


@router.post("/reset_password")
async def reset_password_endpoint(request: Request):
    params = await request.json()
    username = params.get("username", None)
    new_password = params.get("password", None)
    token = params.get("token", None)
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    if not username:
        return {"error": "no user id provided"}
    if not new_password:
        return {"error": "no password provided"}
    dets = await reset_password(username, new_password)
    return dets
