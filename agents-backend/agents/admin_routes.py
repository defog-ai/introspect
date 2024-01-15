from fastapi import APIRouter, Request
import redis
from uuid import uuid4
from db_utils import get_db_conn
from auth_utils import validate_user
import hashlib
import pandas as pd
from io import StringIO
import yaml

env = None
with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

redis_host = env["redis_server_host"]
router = APIRouter()
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

SALT = "TOMMARVOLORIDDLE"
DEFOG_API_KEY = "rishabh"


@router.post("/admin/add_users")
async def add_user(request: Request):
    params = await request.json()
    token = params.get("token")
    user_dets_csv = params.get("user_dets_csv", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    if not user_dets_csv:
        return {"error": "no users information provided"}

    # get the users from the csv
    users = pd.read_csv(StringIO(user_dets_csv)).to_dict(orient="records")

    # create a password for each user
    userdets = []
    for user in users:
        dets = {
            "username": user.get("username", user.get("user_email")),
            "password": user.get("password", user.get("user_password")),
            "user_type": user.get("user_type", user.get("user_role")),
        }
        userdets.append(dets)

    # save the users to postgres
    conn = get_db_conn()
    cur = conn.cursor()
    for dets in userdets:
        hashed_password = hashlib.sha256(
            (dets["username"] + SALT + dets["password"]).encode()
        ).hexdigest()
        cur.execute(
            "INSERT INTO defog_users (username, hashed_password, token, user_type, is_premium) VALUES (%s, %s, %s, %s, %s)",
            (dets["username"], hashed_password, DEFOG_API_KEY, dets["user_type"], True),
        )
    conn.commit()
    conn.close()

    return {"status": "success"}


@router.post("/admin/get_users")
async def get_users(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, user_type FROM defog_users")
    users = cur.fetchall()
    conn.close()

    users = pd.DataFrame(users, columns=["username", "user_type"]).to_dict(
        orient="records"
    )
    return {"users": users}


@router.post("/admin/delete_user")
async def delete_user(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    username = params.get("username", None)
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM defog_users WHERE username = %s", (username,))
    conn.commit()
    conn.close()
    return {"status": "success"}
