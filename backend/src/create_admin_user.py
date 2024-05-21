import time

from db_utils import get_db_conn
import hashlib
import time

SALT = "TOMMARVOLORIDDLE"
INTERNAL_API_KEY = "dummy_api_key"

time.sleep(5)
try:
    con = get_db_conn()
except:
    time.sleep(5)
    con = get_db_conn()
cur = con.cursor()

username = "admin"
password = "admin"
hashed_password = hashlib.sha256((username + SALT + password).encode()).hexdigest()

# check if admin user exists first
admin_exists = False
cur.execute("SELECT * FROM defog_users WHERE username = %s", (username,))
if cur.fetchone():
    admin_exists = True
    print("Admin user already exists.")

if not admin_exists:
    cur.execute(
        "INSERT INTO defog_users (username, hashed_password, token, user_type, is_premium) VALUES (%s, %s, %s, %s, %s)",
        (username, hashed_password, INTERNAL_API_KEY, "admin", True),
    )
    con.commit()
    con.close()
    print("Admin user created.")
