from fastapi import APIRouter, Request
from db_utils import get_db_conn
from auth_utils import validate_user
import hashlib
import pandas as pd
from io import StringIO
from auth_routes import validate_user
import requests
import asyncio

router = APIRouter()

SALT = "TOMMARVOLORIDDLE"
INTERNAL_API_KEY = "DUMMY_KEY"


@router.post("/admin/add_users")
async def add_user(request: Request):
    params = await request.json()
    token = params.get("token")
    gsheets_url = params.get("gsheets_url")
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    if not gsheets_url:
        return {"error": "no google sheets url provided"}

    # get the users from the google sheet
    user_dets_csv = None
    try:
        url_to_query = gsheets_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv&sheet=v4"
        user_dets_csv = await asyncio.to_thread(requests.get, url_to_query)
        user_dets_csv = user_dets_csv.text
    except:
        return {"error": "could not get the google sheet"}

    # get the users from the csv
    try:
        users = pd.read_csv(StringIO(user_dets_csv)).to_dict(orient="records")
        print(users, flush=True)
    except:
        return {"error": "could not parse the google sheets csv"}

    # create a password for each user
    userdets = []
    for user in users:
        dets = {
            "username": user.get("username", user.get("user_email")).lower(),
            "user_type": user.get("user_type", user.get("user_role")).lower(),
        }
        userdets.append(dets)

    # save the users to postgres
    conn = get_db_conn()
    cur = conn.cursor()
    for dets in userdets:
        hashed_password = hashlib.sha256(
            (dets["username"] + SALT + "defog_" + dets["username"]).encode()
        ).hexdigest()

        # check if user already exists
        cur.execute(
            "SELECT * FROM defog_users WHERE username = %s", (dets["username"],)
        )
        user_exists = cur.fetchone()

        if user_exists:
            cur.execute(
                "UPDATE defog_users SET hashed_password = %s, user_type = %s WHERE username = %s",
                (hashed_password, dets["user_type"], dets["username"]),
            )
        else:
            cur.execute(
                "INSERT INTO defog_users (username, hashed_password, token, user_type, is_premium) VALUES (%s, %s, %s, %s, %s)",
                (
                    dets["username"],
                    hashed_password,
                    INTERNAL_API_KEY,
                    dets["user_type"],
                    True,
                ),
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
