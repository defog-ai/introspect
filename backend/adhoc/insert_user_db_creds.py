import copy
import datetime
import hashlib

from db_utils import engine, DbCreds, Users
from sqlalchemy import insert, select, update

SALT = "TOMMARVOLORIDDLE"

# Edit this section based on your data setup
users = [
    {
        "username": "card",
        "password": "password",
        "api_key": "123",
        "user_type": "user",
        "database": "card",
    },
    {
        "username": "housing",
        "password": "password",
        "api_key": "456",
        "user_type": "user",
        "database": "housing",
    },
    {
        "username": "restaurant",
        "password": "password",
        "api_key": "test_restaurant",
        "user_type": "user",
        "database": "restaurants",
    },
    {
        "username": "macmillan",
        "password": "admin",
        "api_key": "test_macmillan",
        "user_type": "admin",
        "database": "macmillan",
    },
]
DB_CREDS = {
    "host": "host.docker.internal",
    "port": "5432",
    "user": "postgres",
    "password": "postgres",
}


# function for getting hashed_password
def get_hashed_password(username, password):
    return hashlib.sha256((username + SALT + password).encode()).hexdigest()


with engine.begin() as conn:
    # insert users and their db_creds
    for user in users:
        username = user["username"]
        password = user["password"]
        hashed_password = get_hashed_password(username, password)
        user_type = user["user_type"]
        api_key = user["api_key"]

        # check if user exists and update
        user_result = conn.execute(
            select(Users).where(Users.token == api_key)
        ).fetchone()
        if user_result:
            conn.execute(
                update(Users)
                .where(Users.token == api_key)
                .values(
                    username=username,
                    hashed_password=hashed_password,
                    user_type=user_type,
                )
            )
            print(f"User {username} updated.")
        else:
            conn.execute(
                insert(Users).values(
                    username=username,
                    hashed_password=hashed_password,
                    token=api_key,
                    user_type=user_type,
                    created_at=datetime.datetime.now(),
                )
            )
            print(f"User {username} created.")

        # check if db_creds exists and update
        db_creds = conn.execute(
            select(DbCreds.db_creds).where(DbCreds.api_key == api_key)
        ).fetchone()
        if db_creds:
            db_creds = copy.deepcopy(DB_CREDS)
            db_creds["database"] = user["database"]
            conn.execute(
                update(DbCreds)
                .where(DbCreds.api_key == api_key)
                .values(
                    db_creds=db_creds,
                )
            )
            print(f"DbCreds for {username} updated.")
        else:
            conn.execute(
                insert(DbCreds).values(
                    api_key=api_key,
                    db_creds=db_creds,
                    db_type="postgres",
                )
            )
            print(f"DbCreds for {username} created.")
