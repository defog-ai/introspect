import hashlib
from db_utils import engine, Users
from sqlalchemy import (
    select,
    update,
)
from fastapi.responses import JSONResponse

SALT = "TOMMARVOLORIDDLE"


def login_user(username, password):
    hashed_password = hashlib.sha256((username + SALT + password).encode()).hexdigest()
    with engine.begin() as conn:
        user = conn.execute(
            select(Users).where(Users.hashed_password == hashed_password)
        ).fetchone()

    if user:
        return {"status": "success", "user_type": user[0], "token": hashed_password}
    else:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )


def reset_password(username, new_password):
    hashed_password = hashlib.sha256(
        (username + SALT + new_password).encode()
    ).hexdigest()
    with engine.begin() as conn:
        conn.execute(
            update(Users)
            .where(Users.username == username)
            .values(hashed_password=hashed_password)
        )


def get_hashed_password(username, password):
    return hashlib.sha256((username + SALT + password).encode()).hexdigest()


def get_hashed_username(username):
    return hashlib.sha256((username + SALT).encode()).hexdigest()


def validate_user_email(email):
    with engine.begin() as conn:
        user = conn.execute(select(Users).where(Users.username == email)).fetchone()
    if user:
        return True
    else:
        return False
