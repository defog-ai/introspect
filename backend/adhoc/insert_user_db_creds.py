import copy
import datetime
import hashlib

from db_utils import engine, DbCreds, Users
from sqlalchemy import insert, select, update

SALT = "TOMMARVOLORIDDLE"

# Edit this section based on your data setup
users = [
    {
        "username": "admin",
        "password": "admin",
    },
    {
        "username": "card",
        "password": "password",
    },
    {
        "username": "housing",
        "password": "password",
    },
    {
        "username": "restaurant",
        "password": "password",
    },
    {
        "username": "macmillan",
        "password": "admin",
    },
    {
        "username": "webshop",
        "password": "test",
    },
    {
        "username": "cricket",
        "password": "test",
    }
]
databases = [
    {
        "api_key": "123",
        "database": "card",
    },
    {
        "api_key": "456",
        "database": "housing",
    },
    {
        "api_key": "test_restaurant",
        "database": "restaurants",
    },
    {
        "api_key": "test_macmillan",
        "database": "macmillan",
    },
    {
        "api_key": "fbc046431bd131d1c6c55c782d8bbd413a339d9c78ec6da6fea73cdfaeacb897",
        "database": "macmillan",
    },
    {
        "api_key": "test_webshop",
        "database": "webshop",
    },
    {
        "api_key": "test_cricket",
        "database": "cricket",
    }
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

        # check if user exists and update
        user_result = conn.execute(
            select(Users).where(Users.username == username)
        ).fetchone()
        if user_result:
            conn.execute(
                update(Users)
                .where(Users.username == username)
                .values(
                    username=username,
                    hashed_password=hashed_password,
                    user_type="admin",
                )
            )
            print(f"User {username} updated.")
        else:
            conn.execute(
                insert(Users).values(
                    username=username,
                    hashed_password=hashed_password,
                    token=hashed_password,
                    user_type="admin",
                    created_at=datetime.datetime.now(),
                )
            )
            print(f"User {username} created.")
        print(f"Token to use for {username}: {hashed_password}")

    for db in databases:
        api_key = db["api_key"]
        database = db["database"]
        # check if db_creds exists and update
        db_creds = conn.execute(
            select(DbCreds.db_creds).where(DbCreds.api_key == api_key)
        ).fetchone()
        if db_creds:
            db_creds = copy.deepcopy(DB_CREDS)
            db_creds["database"] = database
            conn.execute(
                update(DbCreds)
                .where(DbCreds.api_key == api_key)
                .values(
                    db_creds=db_creds,
                    db_type="postgres",
                )
            )
            print(f"DbCreds for api_key={api_key} updated.")
        else:
            db_creds = copy.deepcopy(DB_CREDS)
            db_creds["database"] = database
            conn.execute(
                insert(DbCreds).values(
                    api_key=api_key,
                    db_creds=db_creds,
                    db_type="postgres",
                )
            )
            print(f"DbCreds for api_key={api_key} created.")
