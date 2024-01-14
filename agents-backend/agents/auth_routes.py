from fastapi import APIRouter, Request
from auth_utils import login_user, reset_password, validate_user

router = APIRouter()

@router.post("/login")
async def login(request: Request):
    params = await request.json()
    user_id = params.get("user_id", None)
    password = params.get("password", None)
    if not user_id:
        return {
            "error": "no user id provided"
        }
    if not password:
        return {
            "error": "no password provided"
        }
    
    dets = login_user(user_id, password)
    return dets

@router.post("/reset_password")
async def reset_password(request: Request):
    params = await request.json()
    user_id = params.get("user_id", None)
    new_password = params.get("password", None)
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {
            "error": "unauthorized"
        }
    if not user_id:
        return {
            "error": "no user id provided"
        }
    if not new_password:
        return {
            "error": "no password provided"
        }
    dets = reset_password(user_id, new_password)
    return dets