from fastapi import APIRouter, Request, HTTPException
from auth_utils import login_user, reset_password, validate_user, get_hashed_password
from google.oauth2 import id_token
from google.auth.transport import requests
import asyncio
import os

INTERNAL_API_KEY = "DUMMY_KEY"
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]

router = APIRouter()


@router.post("/login")
async def login(request: Request):
    params = await request.json()
    username = params.get("username", None)
    password = params.get("password", None)
    if not username:
        return {"error": "no user id provided"}
    if not password:
        return {"error": "no password provided"}

    dets = login_user(username, password)
    return dets


async def validate_google_token(token: str):
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = await asyncio.to_thread(
            id_token.verify_oauth2_token, token, requests.Request(), GOOGLE_CLIENT_ID
        )

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        user_id = idinfo["sub"]
        # You can also get other information from the token, like the user's email:
        user_email = idinfo.get("email")
        hashed_password = get_hashed_password(user_email, "defog_" + user_email)

        # Check if user exists
        if validate_user(hashed_password):
            print("User exists", flush=True)
            dets = login_user(user_email, "defog_" + user_email)
            dets["user_email"] = user_email
            return dets
        else:
            return {
                "error": "user is not registered with the system. Please contact the administrator."
            }
    except ValueError:
        # Invalid token
        return {
            "status": "unauthorized",
        }


@router.post("/login_google")
async def login_google(request: Request):
    body = await request.json()
    token = body.get("credential")
    if not token:
        raise HTTPException(status_code=400, detail="Missing Google ID token.")
    return await validate_google_token(token)


@router.post("/reset_password")
async def reset_password(request: Request):
    params = await request.json()
    username = params.get("username", None)
    new_password = params.get("password", None)
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}
    if not username:
        return {"error": "no user id provided"}
    if not new_password:
        return {"error": "no password provided"}
    dets = reset_password(username, new_password)
    return dets
