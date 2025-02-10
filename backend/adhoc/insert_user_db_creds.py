import copy
import datetime
import hashlib
import os

from auth_utils import get_hashed_username
from db_models import DbCreds, Users
from sqlalchemy import create_engine, insert, select, update

SALT = os.getenv("SALT")
if not SALT:
    raise ValueError("SALT is not set")
elif SALT == "default_salt":
    raise ValueError("SALT is the default value. Please set a custom value.")

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
    }
]
databases = [
    {
        "api_key": "Card",
        "database": "card",
    },
    {
        "api_key": "Housing",
        "database": "housing",
    },
    {
        "api_key": "Restaurant",
        "database": "restaurants",
    },
    {
        "api_key": "Macmillan",
        "database": "macmillan",
    },
    {
        "api_key": "Macmillan",
        "database": "macmillan",
    },
    {
        "api_key": "Webshop",
        "database": "webshop",
    },
    {
        "api_key": "Cricket",
        "database": "cricket",
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
