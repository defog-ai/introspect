import hashlib
import os

from db_models import Users
from sqlalchemy import create_engine, select, insert

SALT = "TOMMARVOLORIDDLE"
INTERNAL_API_KEY = "dummy_api_key"

username = "admin"
password = "admin"
hashed_password = hashlib.sha256((username + SALT + password).encode()).hexdigest()

# check if admin user exists first
admin_exists = False

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
    user = conn.execute(select(Users).where(Users.username == username)).fetchone()

if user:
    admin_exists = True
    print("Admin user already exists.")
else:
    print("Creating admin user...")
    with engine.begin() as conn:
        conn.execute(
            insert(Users).values(
                username=username,
                hashed_password=hashed_password,
                token=INTERNAL_API_KEY,
                user_type="admin",
            )
        )
    print("Admin user created.")
