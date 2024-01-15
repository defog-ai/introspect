import hashlib
from db_utils import get_db_conn

SALT = "TOMMARVOLORIDDLE"


def validate_user(token, user_type=None):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_type FROM defog_users WHERE hashed_password = %s", (token,)
    )
    user = cur.fetchone()
    conn.close()
    if user:
        if user_type == "admin":
            if user[0] == "admin":
                return True
    else:
        return False


def login_user(username, password):
    hashed_password = hashlib.sha256((username + SALT + password).encode()).hexdigest()
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_type FROM defog_users WHERE hashed_password = %s",
        (hashed_password,),
    )
    user = cur.fetchone()
    conn.close()
    if user:
        return {"status": "success", "user_type": user[0], "token": hashed_password}
    else:
        return {
            "status": "unauthorized",
        }


def reset_password(username, new_password):
    hashed_password = hashlib.sha256(
        (username + SALT + new_password).encode()
    ).hexdigest()
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE defog_users SET hashed_password = %s WHERE username = %s",
        (hashed_password, username),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}
