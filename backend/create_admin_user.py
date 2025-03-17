# This script is used to create an admin user in the database during the
# first deployment of the backend.
#
# This script is idempotent, meaning it can be run multiple times without
# causing an error.

import hashlib
import os
from datetime import datetime

from db_models import Users, UserType, UserStatus
from sqlalchemy import create_engine, select, insert, update

SALT = os.getenv("SALT", "default_salt")

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
    
    # Ensure user has correct user_type and status
    with engine.begin() as conn:
        conn.execute(
            update(Users)
            .where(Users.username == username)
            .values(
                user_type=UserType.ADMIN,
                status=UserStatus.ACTIVE
            )
        )
    print("Admin user properties updated to ensure correct role and status.")
else:
    print("Creating admin user...")
    with engine.begin() as conn:
        conn.execute(
            insert(Users).values(
                username=username,
                hashed_password=hashed_password,
                token=hashed_password,
                user_type=UserType.ADMIN,
                status=UserStatus.ACTIVE,
                created_at=datetime.now()
            )
        )
    print("Admin user created. Please reset the default admin password when you log in.")
    print("WARNING: The default admin credentials are: username='admin', password='admin'")
    print("Change these credentials immediately after first login!")
