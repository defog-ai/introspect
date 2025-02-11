from fastapi import APIRouter, Request, HTTPException
from auth_utils import login_user, reset_password, get_hashed_username, validate_user
from google.oauth2 import id_token
from google.auth.transport import requests
import asyncio
import os
from fastapi.responses import JSONResponse

from request_models import LoginRequest
from utils_logging import LOGGER

INTERNAL_API_KEY = "DUMMY_KEY"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

router = APIRouter()


@router.post("/login")
async def login(req: LoginRequest):
    token = await login_user(req.username, req.password)
    if token:
        return {
            "status": "success",
            "user_type": "admin",  # TODO: remove after frontend references have been removed
            "token": token,
        }
    else:
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
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = await asyncio.to_thread(
            id_token.verify_oauth2_token, token, requests.Request(), GOOGLE_CLIENT_ID
        )

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        user_email = idinfo.get("email")
        hashed_password = get_hashed_username(user_email)

        # Check if user exists
        if await validate_user(hashed_password):
            token = await login_user(user_email, "")
            return {
                "status": "success",
                "user_type": "admin",  # TODO: remove after frontend references have been removed
                "token": token,
            }
        else:
            return {
                "error": "user is not registered with the system. Please contact the administrator."
            }
    except ValueError:
        # Invalid token
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
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
