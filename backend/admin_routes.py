from fastapi import APIRouter, Request
from sqlalchemy import (
    select,
    update,
    insert,
    delete,
)
from db_utils import engine, Users, validate_user
import hashlib
import pandas as pd
from io import StringIO
import requests
import asyncio
from fastapi.responses import JSONResponse
import os

router = APIRouter()

SALT = "TOMMARVOLORIDDLE"
INTERNAL_API_KEY = "DUMMY_KEY"


@router.post("/admin/add_users")
async def add_user(request: Request):
    params = await request.json()
    token = params.get("token")
    gsheets_url = params.get("gsheets_url")
    user_dets_csv = params.get("users_csv")
    if not (await validate_user(token, user_type="admin")):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    if not gsheets_url and not user_dets_csv:
        return {"error": "no user details, CSV, or google sheet url provided"}

    # get the users from the google sheet
    if gsheets_url:
        try:
            url_to_query = (
                gsheets_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv&sheet=v4"
            )
            user_dets_csv = await asyncio.to_thread(requests.get, url_to_query)
            user_dets_csv = user_dets_csv.text
        except:
            return {"error": "could not get the google sheet"}

    # get the users from the csv
    try:
        users = (
            pd.read_csv(StringIO(user_dets_csv)).fillna("").to_dict(orient="records")
        )
    except:
        return {
            "error": "could not parse the file successfully - are you sure it's a valid CSV?"
        }

    # create a password for each user
    userdets = []
    for user in users:
        dets = {
            "username": user.get("username", user.get("user_email")).lower(),
            "user_type": user.get("user_type", user.get("user_role")).lower(),
            "password": user.get("password", user.get("user_password")),
            # "allowed_dbs": user.get("allowed_dbs", ""),
        }
        userdets.append(dets)

    # save the users to postgres
    async with engine.begin() as conn:
        for dets in userdets:
            if dets["password"]:
                hashed_password = hashlib.sha256(
                    (dets["username"] + SALT + dets["password"]).encode()
                ).hexdigest()
            else:
                hashed_password = hashlib.sha256(
                    (dets["username"] + SALT).encode()
                ).hexdigest()

            # check if user already exists
            user_exists = await conn.execute(
                select(Users).where(Users.username == dets["username"])
            )

            user_exists = user_exists.fetchone()

            if user_exists:
                await conn.execute(
                    update(Users)
                    .where(Users.username == dets["username"])
                    .values(
                        hashed_password=hashed_password,
                        user_type=dets["user_type"],
                        # allowed_dbs=dets["allowed_dbs"],
                    )
                )
            else:
                await conn.execute(
                    insert(Users).values(
                        username=dets["username"],
                        hashed_password=hashed_password,
                        token=INTERNAL_API_KEY,
                        user_type=dets["user_type"],
                        # allowed_dbs=dets["allowed_dbs"],
                    )
                )

    return {"status": "success"}


@router.post("/admin/get_users")
async def get_users(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not (await validate_user(token, user_type="admin")):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    async with engine.begin() as conn:
        users = await conn.execute(select(Users))
        users = users.fetchall()

    users = pd.DataFrame(users)[["username", "user_type"]]
    users["allowed_dbs"] = ""
    users = users.to_dict(orient="records")
    return {"users": users}


@router.post("/admin/delete_user")
async def delete_user(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not (await validate_user(token, user_type="admin")):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    username = params.get("username", None)
    async with engine.begin() as conn:
        await conn.execute(delete(Users).where(Users.username == username))
    return {"status": "success"}


@router.post("/get_non_admin_config")
async def get_non_admin_config(request: Request):
    # get environment variables:
    # HIDE_SQL_TAB_FOR_NON_ADMIN
    # HIDE_PREVIEW_TABS_FOR_NON_ADMIN
    # HIDDEN_CHARTS_FOR_NON_ADMIN
    hide_sql_tab_for_non_admin = os.getenv("HIDE_SQL_TAB_FOR_NON_ADMIN")
    hide_preview_tabs_for_non_admin = os.getenv("HIDE_PREVIEW_TABS_FOR_NON_ADMIN")
    hidden_charts_for_non_admin = os.getenv("HIDDEN_CHARTS_FOR_NON_ADMIN")
    hide_raw_analysis_for_non_admin = os.getenv("HIDE_RAW_ANALYSIS_FOR_NON_ADMIN")
    if hidden_charts_for_non_admin:
        hidden_charts_for_non_admin = [
            x.strip().lower() for x in hidden_charts_for_non_admin.split(",")
        ]

    return JSONResponse(
        status_code=200,
        content={
            "hide_sql_tab_for_non_admin": hide_sql_tab_for_non_admin == "yes"
            or hide_sql_tab_for_non_admin == "true",
            "hide_preview_tabs_for_non_admin": hide_preview_tabs_for_non_admin == "yes"
            or hide_preview_tabs_for_non_admin == "true",
            "hidden_charts_for_non_admin": hidden_charts_for_non_admin,
            "hide_raw_analysis_for_non_admin": hide_raw_analysis_for_non_admin == "yes"
            or hide_raw_analysis_for_non_admin == "true",
        },
    )


@router.post("/admin/add_user_with_token")
async def add_user_with_token(request: Request):
    params = await request.json()
    auth_token = params.get("auth_token")
    user_token = params.get("user_token")
    username = params.get("username")
    user_type = params.get("user_type")
    if not (await validate_user(auth_token, user_type="admin")):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    async with engine.begin() as conn:
        # if user already exists, update the token
        user = await conn.execute(select(Users).where(Users.username == username))
        user = user.fetchone()
        if user:
            await conn.execute(
                update(Users)
                .where(Users.username == username)
                .values(
                    hashed_password=user_token,  # this is horribly confusing nomenclature, but me from 7 months ago did this monstrosity. So I guess we just roll with it 🤦🏽‍♂️
                    token=INTERNAL_API_KEY,
                    user_type=user_type,
                )
            )
        else:
            await conn.execute(
                insert(Users).values(
                    username=username,
                    hashed_password=user_token,  # this is horribly confusing nomenclature, but me from 7 months ago did this monstrosity. So I guess we just roll with it 🤦🏽‍♂️
                    token=INTERNAL_API_KEY,
                    user_type=user_type,
                )
            )

    return {"status": "success"}
