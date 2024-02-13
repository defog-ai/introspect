from fastapi import APIRouter, Request
from auth_utils import login_user, reset_password, validate_user
import jwt
import asyncio
import hashlib
from db_utils import get_db_conn

SALT = "TOMMARVOLORIDDLE"
DEFOG_API_KEY = "genmab-survival-test"

router = APIRouter()

@router.post("/validate_ms_sso")
async def validate_ms_sso(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not token:
        return {"error": "no token provided"}
    
    try:
        decoded = await asyncio.to_thread(jwt.decode, token, options={"verify_signature": False})
        username = decoded.get("preferred_username", None)
        if not username:
            return {"error": "invalid token"}
        oid = decoded.get("oid", None)
        hashed_password = hashlib.sha256((username + SALT + oid).encode()).hexdigest()
        if not validate_user(hashed_password):
            # if user does not exist, create the user
            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO defog_users (username, hashed_password, token, user_type, is_premium) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, DEFOG_API_KEY, "user", True),
            )
            cur.close()
            conn.commit()
            conn.close()
        
        return {"status": "success", "user_type": "user", "token": hashed_password, "user": username}
    except jwt.PyJWTError as e:
        print(e)
        return {"error": "invalid token"}

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
