import hashlib

from db_utils import engine, Users
from sqlalchemy import select, insert

SALT = "TOMMARVOLORIDDLE"
INTERNAL_API_KEY = "dummy_api_key"

username = "admin"
password = "admin"
hashed_password = hashlib.sha256((username + SALT + password).encode()).hexdigest()

# check if admin user exists first
admin_exists = False

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
