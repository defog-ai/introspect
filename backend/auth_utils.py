import hashlib
from db_utils import engine, Users
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
