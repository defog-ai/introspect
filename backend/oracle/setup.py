# This script just checks for a few things like file directory structure
# and creates them if they don't exist
import os
import sqlite3

CREATE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    report_name TEXT,
    status TEXT,
    date_created TEXT,
    api_key VARCHAR(255),
    username TEXT,
    inputs TEXT,
    outputs TEXT,
    feedback TEXT
);
"""
CREATE_CLARIFICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS clarifications (
    clarification_id TEXT,
    report_id TEXT,
    llm_question TEXT,
    user_response TEXT
);
"""

def setup_dir(app_root_path: str):
    oracle_path = os.path.join(app_root_path, "oracle")
    if not os.path.exists(oracle_path):
        os.makedirs(oracle_path)
        print("Created oracle directory.")
    oracle_reports_path = os.path.join(oracle_path, "reports")
    if not os.path.exists(oracle_reports_path):
        os.makedirs(oracle_reports_path)
        print("Created reports directory.")
    oracle_sqlite_db_path = os.path.join(oracle_path, "data.db")
    if not os.path.exists(oracle_sqlite_db_path):
        print("Database not found. Creating a new one.")
        conn = sqlite3.connect(oracle_sqlite_db_path)
        c = conn.cursor()
        c.execute(CREATE_REPORTS_TABLE)
        c.execute(CREATE_CLARIFICATIONS_TABLE)
        conn.commit()
        conn.close()
        print("SQLite3 Database for Oracle created.")
    else:
        # test connection
        try:
            conn = sqlite3.connect(oracle_sqlite_db_path)
            # check if tables exist
            c = conn.cursor()
            c.execute("SELECT * FROM reports")
            c.execute("SELECT * FROM clarifications")
            conn.close()
            print("SQLite3 Database for Oracle found.")
        except sqlite3.Error:
            print("SQLite3 Database for Oracle not found.")
        finally:
            if "conn" in locals():
                conn.close()