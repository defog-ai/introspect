"""Pytest configuration and shared fixtures for the Defog backend tests.

This module provides the core test infrastructure including:
1. Database setup and cleanup for integration tests
2. Authentication fixtures (e.g., admin_token)
3. Shared configuration constants (e.g., database credentials, API endpoints)
4. Automatic cleanup of test data after test sessions

The fixtures and utilities in this file are automatically discovered and used by pytest,
making them available to all test files in the test suite without explicit imports.
This centralization helps maintain consistency across tests and reduces code duplication.
"""

import os
import sys
import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db_models import DbCreds

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Configuration
BASE_URL = "http://localhost:1235"  # Backend server port

# Database credentials of the docker postgres container
DOCKER_DB_CREDS = {
    "user": os.environ.get("DEFOG_DBUSER", "postgres"),
    "password": os.environ.get("DEFOG_DBPASSWORD", "postgres"),
    "host": os.environ.get("DEFOG_DBHOST", "agents-postgres"),
    "port": os.environ.get("DEFOG_DBPORT", "5432"),
    "database": os.environ.get("DEFOG_DATABASE", "postgres"),
}

# Test database configuration
TEST_DB = {
    "db_name": "test_db",
    "database": "test_db",
    "db_type": "postgres",
    "db_creds": {
        "host": "host.docker.internal",
        "port": 5432,
        "database": "test_db",
        "user": "postgres",
        "password": "postgres",
    },
}

USERNAME = "admin"
PASSWORD = "admin"


def setup_test_database():
    """Setup test database locally with the required schema.
    This only handles local database creation and schema setup.
    The registration of database credentials is tested separately.
    """
    # Setup the test database in user's local Postgres
    local_db_creds = {
        "user": "postgres",
        "password": "postgres",
        "host": "host.docker.internal",
        "port": "5432",
        "database": "postgres",
    }

    # Connect to local postgres to create test_db
    local_uri = f"postgresql://{local_db_creds['user']}:{local_db_creds['password']}@{local_db_creds['host']}:{local_db_creds['port']}/{local_db_creds['database']}"
    local_engine = create_engine(local_uri)

    with local_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # Disconnect users from test_db if it exists
        conn.execute(
            text(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'test_db'
                AND pid <> pg_backend_pid();
                """
            )
        )

        # Drop and recreate test_db
        conn.execute(text("DROP DATABASE IF EXISTS test_db;"))
        conn.execute(text("CREATE DATABASE test_db;"))

    # Connect to test_db and setup schema
    test_db_uri = f"postgresql://{local_db_creds['user']}:{local_db_creds['password']}@{local_db_creds['host']}:{local_db_creds['port']}/test_db"
    test_engine = create_engine(test_db_uri)

    # Read and execute the SQL setup file
    sql_file_path = os.path.join(os.path.dirname(__file__), "test_db.sql")
    with open(sql_file_path, "r") as f:
        sql_setup = f.read()

    with test_engine.begin() as conn:
        conn.execute(text(sql_setup))


def setup_test_db_name():
    """Setup test database name in DbCreds table using SQLAlchemy ORM."""
    
    # Connect to the database where DbCreds table exists
    docker_uri = f"postgresql://{DOCKER_DB_CREDS['user']}:{DOCKER_DB_CREDS['password']}@{DOCKER_DB_CREDS['host']}:{DOCKER_DB_CREDS['port']}/{DOCKER_DB_CREDS['database']}"
    engine = create_engine(docker_uri)
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        # Check if db_name already exists
        existing_db = session.query(DbCreds).filter_by(db_name=TEST_DB["db_name"]).first()
        
        if not existing_db:
            # Create new DbCreds entry
            new_db_cred = DbCreds(db_name=TEST_DB["db_name"])
            session.add(new_db_cred)
            session.commit()


@pytest.fixture
def admin_token():
    """Get admin token for authentication reusable across all the integration API tests as a fixture"""
    response = requests.post(
        f"{BASE_URL}/login", json={"username": USERNAME, "password": PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    return data["token"]


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """
    Cleanup fixture that runs once per session.
    After all tests finish, it removes everything related to the test_db from the database.
    """
    setup_test_database()
    setup_test_db_name()

    yield

    # --- Cleanup code runs here, *after* all tests have completed ---
    print("\n--- Running cleanup for test_db ---")
    try:
        db_name = TEST_DB["db_name"]

        # 1. Get admin token for verification
        response = requests.post(
            f"{BASE_URL}/login", json={"username": USERNAME, "password": PASSWORD}
        )
        if response.status_code != 200:
            print("Failed to get admin token for cleanup verification.")
            return
        admin_token = response.json()["token"]

        # 2. Clean up all tables in the docker postgres container
        # Use the global DOCKER_DB_CREDS
        docker_uri = f"postgresql://{DOCKER_DB_CREDS['user']}:{DOCKER_DB_CREDS['password']}@{DOCKER_DB_CREDS['host']}:{DOCKER_DB_CREDS['port']}/{DOCKER_DB_CREDS['database']}"
        docker_engine = create_engine(docker_uri)

        with docker_engine.begin() as conn:
            # Delete from all tables where db_name is a column
            tables_with_db_name = [
                "metadata", "table_info", "instructions", "golden_queries",
                "imported_tables", "analyses", "oracle_guidelines", 
                "oracle_analyses", "oracle_sources", "db_creds"
            ]
            
            for table in tables_with_db_name:
                conn.execute(text(f"DELETE FROM {table} WHERE db_name = :db_name"), {"db_name": db_name})

            # Delete from oracle_reports where db_name is in a JSON column
            conn.execute(text("DELETE FROM oracle_reports WHERE db_name = :db_name"), {"db_name": db_name})

            # Delete any users created during tests
            conn.execute(text("DELETE FROM users WHERE username != :admin_user"), {"admin_user": USERNAME})

        # 3. Verify db_creds are deleted by calling get_tables_db_creds
        response = requests.post(
            f"{BASE_URL}/integration/get_tables_db_creds",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200 and not response.json().get("error"):
            print("Warning: Database credentials still exist after cleanup!")

        # 4. Drop the test database
        # Setup connection to postgres database
        local_db_creds = {
            "user": "postgres",
            "password": "postgres",
            "host": "host.docker.internal",
            "port": "5432",
            "database": "postgres",
        }
        local_uri = f"postgresql://{local_db_creds['user']}:{local_db_creds['password']}@{local_db_creds['host']}:{local_db_creds['port']}/{local_db_creds['database']}"
        local_engine = create_engine(local_uri)

        with local_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = 'test_db'
                    AND pid <> pg_backend_pid();
                    """
                )
            )
            conn.execute(text("DROP DATABASE IF EXISTS test_db;"))

        print("--- Test cleanup completed successfully ---")

    except Exception as e:
        print(f"Cleanup failed with error: {str(e)}")
