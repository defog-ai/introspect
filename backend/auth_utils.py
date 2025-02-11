import hashlib
import os
from typing import Optional

from fastapi import HTTPException, Request
from db_config import engine
from db_models import Users
from sqlalchemy import (
    select,
    update,
    and_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from utils_logging import LOGGER

SALT = os.getenv("SALT", "default_salt")
if SALT == "default_salt":
    LOGGER.info("SALT is the default value. Please set a custom value if you require a more secure authentication.")


async def login_user(username: str, password: str | None = None) -> Optional[str]:
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
    async with engine.begin() as conn:
        user = await conn.execute(select(Users).where(Users.username == email))
        user = user.fetchone()
    if user:
        return True
    else:
        return False

async def validate_user(api_key: str, **kwargs) -> Optional[Users]:
    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = select(Users).where(Users.token == api_key)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
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
