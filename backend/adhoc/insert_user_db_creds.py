import copy
import datetime
import hashlib
import os

from auth_utils import get_hashed_username
from db_models import DbCreds, Users
from sqlalchemy import create_engine, insert, select, update


SALT = os.getenv("SALT", "default_salt")

# Edit this section based on your data setup
users = [
    {
        "username": "admin",
        "password": "admin",
    },
    {
        "username": "Card",
        "password": "password",
    },
    {
        "username": "Housing",
        "password": "password",
    },
    {
        "username": "Restaurant",
        "password": "password",
    },
    {
        "username": "Macmillan",
        "password": "admin",
    },
    {
        "username": "Webshop",
        "password": "test",
    },
    {
        "username": "Cricket",
        "password": "test",
    },
    {
        "username": "jp@defog.ai",
    },
    {
        "username": "wendy@defog.ai",
    },
    {
        "username": "Coffee Export",
        "password": "test",
    }
]
databases = [
    {
        "db_name": "Card",   # db_name is what we typically call api_key
        "database": "card",  # name of the database in defog-data
    },
    {
        "db_name": "Housing",
        "database": "housing",
    },
    {
        "db_name": "Restaurant",
        "database": "restaurants",
    },
    {
        "db_name": "Macmillan",
        "database": "macmillan",
    },
    {
        "db_name": "Macmillan",
        "database": "macmillan",
    },
    {
        "db_name": "Webshop",
        "database": "webshop",
    },
    {
        "db_name": "Cricket",
        "database": "cricket",
    },
    {
        "db_name": "Coffee Export",
        "database": "coffee_export",
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


db_creds = {
    "user": os.environ.get("DBUSER", "postgres"),
    "password": os.environ.get("DBPASSWORD", "postgres"),
    "host": os.environ.get("DBHOST", "agents-postgres"),
    "port": os.environ.get("DBPORT", "5432"),
    "database": os.environ.get("DATABASE", "postgres"),
}

# connect to the main database
connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
engine = create_engine(connection_uri, echo=True)

with engine.begin() as conn:
    # insert users and their db_creds
    for user in users:
        username = user["username"]
        password = user.get("password")
        if password:
            hashed_password = get_hashed_password(username, password)
        else:
            hashed_password = get_hashed_username(username)

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
                    token=hashed_password,
                )
            )
            print(f"User {username} updated.")
        else:
            conn.execute(
                insert(Users).values(
                    username=username,
                    hashed_password=hashed_password,
                    token=hashed_password,
                    created_at=datetime.datetime.now(),
                )
            )
            print(f"User {username} created.")
        print(f"Token to use for {username}: {hashed_password}")

    for db in databases:
        db_name = db["db_name"]
        database = db["database"]
        # check if db_creds exists and update
        db_creds = conn.execute(
            select(DbCreds.db_creds).where(DbCreds.db_name == db_name)
        ).fetchone()
        if db_creds:
            db_creds = copy.deepcopy(DB_CREDS)
            db_creds["database"] = database
            conn.execute(
                update(DbCreds)
                .where(DbCreds.db_name == db_name)
                .values(
                    db_creds=db_creds,
                    db_type="postgres",
                )
            )
            print(f"DbCreds for db_name={db_name} updated.")
        else:
            db_creds = copy.deepcopy(DB_CREDS)
            db_creds["database"] = database
            conn.execute(
                insert(DbCreds).values(
                    db_name=db_name,
                    db_creds=db_creds,
                    db_type="postgres",
                )
            )
            print(f"DbCreds for db_name={db_name} created.")
