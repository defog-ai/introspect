import hashlib
from db_config import engine
from db_models import Users
from sqlalchemy import (
    select,
    update,
    and_,
)
from fastapi.responses import JSONResponse

SALT = "TOMMARVOLORIDDLE"


async def login_user(username, password):
    hashed_password = hashlib.sha256((username + SALT + password).encode()).hexdigest()
    hashed_username = hashlib.sha256((username + SALT).encode()).hexdigest()
    async with engine.begin() as conn:
        if password:
            user = await conn.execute(
                select(Users).where(
                    and_(
                        Users.hashed_password == hashed_password,
                        Users.username == username,
                    )
                )
            )
            user = user.fetchone()
        else:
            user = await conn.execute(
                select(Users).where(
                    and_(
                        Users.hashed_password == hashed_username,
                        Users.username == username,
                    )
                )
            )
            user = user.fetchone()

    if user:
        return {
            "status": "success",
            "user_type": user.user_type,
            "token": hashed_password,
        }
    else:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )


async def reset_password(username, new_password):
    hashed_password = hashlib.sha256(
        (username + SALT + new_password).encode()
    ).hexdigest()
    async with engine.begin() as conn:
        await conn.execute(
            update(Users)
            .where(Users.username == username)
            .values(hashed_password=hashed_password)
        )


def get_hashed_password(username, password):
    return hashlib.sha256((username + SALT + password).encode()).hexdigest()


def get_hashed_username(username):
    return hashlib.sha256((username + SALT).encode()).hexdigest()


async def validate_user_email(email):
    async with engine.begin() as conn:
        user = await conn.execute(select(Users).where(Users.username == email))
        user = user.fetchone()
    if user:
        return True
    else:
        return False

async def validate_user(token, user_type=None, get_username=False):
    async with engine.begin() as conn:
        user = await conn.execute(select(Users).where(Users.hashed_password == token))
        user = user.fetchone()
    if user:
        if user_type == "admin":
            if user.user_type == "admin":
                if get_username:
                    return user.username
                else:
                    return True
            else:
                return False
        else:
            if get_username:
                return user.username
            else:
                return True
    else:
        return False
