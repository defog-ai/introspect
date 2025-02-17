import hashlib
import os
from typing import Optional

from fastapi import HTTPException, Request
from db_models import Users
from sqlalchemy import (
    select,
    update,
    and_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from utils_logging import LOGGER


################################################################################
# All imports from db_config in this file are inside respective functions.
# This is to prevent a race condition inside startup.py because this file is imported there.
# Because of the auth_utils import in startup.py, and a top level db_config import in this file
# There would be two simultaneous calls to `CREATE DATABASE` inside the `get_db_engine` function in `db_config.py`.
# The two calls would cause a race condition in `get_db_engine` where the database would not be found in an `exists` check
# but by the time the following statements were run, the _other_ call to CREATE DATABASE would have completed.
# Causing a duplicate key error.
# Also detailed here: https://github.com/defog-ai/defog-self-hosted/pull/385
################################################################################

SALT = os.getenv("SALT", "default_salt")
if SALT == "default_salt":
    LOGGER.info(
        "SALT is the default value. Please set a custom value if you require a more secure authentication."
    )


async def login_user(username: str, password: str | None = None) -> Optional[str]:
    from db_config import engine

    async with AsyncSession(engine) as session:
        async with session.begin():
            if password:
                hashed_password = get_hashed_password(username, password)
            else:
                hashed_password = get_hashed_username(username)
            result = await session.execute(
                select(Users).where(
                    and_(
                        Users.hashed_password == hashed_password,
                        Users.username == username,
                    )
                )
            )
            user = result.scalar_one_or_none()
            return user.token if user else None


async def reset_password(username, new_password):
    from db_config import engine

    hashed_password = hashlib.sha256(
        (username + SALT + new_password).encode()
    ).hexdigest()
    async with engine.begin() as conn:
        await conn.execute(
            update(Users)
            .where(Users.username == username)
            .values(hashed_password=hashed_password, token=hashed_password)
        )


def get_hashed_password(username, password):
    return hashlib.sha256((username + SALT + password).encode()).hexdigest()


def get_hashed_username(username):
    return hashlib.sha256((username + SALT).encode()).hexdigest()


async def validate_user_email(email):
    from db_config import engine

    async with engine.begin() as conn:
        user = await conn.execute(select(Users).where(Users.username == email))
        user = user.fetchone()
    if user:
        return True
    else:
        return False


async def validate_user(token: str) -> Optional[Users]:
    from db_config import engine

    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = select(Users).where(Users.token == token)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                session.expunge(user)
    return user


async def validate_user_request(request: Request):
    """
    Function to be used as a dependency to validate the user request.
    Should be used for all routes that require user validation, ideally during
    the router initialization.
    """
    params = await request.json()
    token = params.get("token")
    user = await validate_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
