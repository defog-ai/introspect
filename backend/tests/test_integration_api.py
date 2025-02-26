import pytest
import requests
import json
import os
from unittest.mock import patch
from sqlalchemy import create_engine, insert, select, update, text
from db_models import DbCreds

# Configuration
BASE_URL = "http://localhost:1235"  # Backend server port

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
    """Setup test database in the system"""
    # Database connection settings for main postgres database
    db_creds = {
        "user": os.environ.get("DBUSER", "postgres"),
        "password": os.environ.get("DBPASSWORD", "postgres"),
        "host": os.environ.get("DBHOST", "agents-postgres"),
        "port": os.environ.get("DBPORT", "5432"),
        "database": os.environ.get("DATABASE", "postgres"),
    }

    # Connect to the main database
    connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
    engine = create_engine(connection_uri)

    # Create test database if it doesn't exist
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # Disconnect all users from the database if it exists
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

        # Drop database if exists and create it
        conn.execute(text("DROP DATABASE IF EXISTS test_db;"))
        conn.execute(text("CREATE DATABASE test_db;"))

    # Now connect to the test database to create tables
    test_db_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/test_db"
    test_engine = create_engine(test_db_uri)

    # Create necessary tables
    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100)
            );
            
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                amount DECIMAL
            );
            
            CREATE TABLE IF NOT EXISTS instructions (
                db_name TEXT PRIMARY KEY,
                sql_instructions TEXT,
                join_hints JSONB
            );
        """
            )
        )

    # Now connect back to postgres database to update credentials
    with engine.begin() as conn:
        # Insert test database credentials
        db_name = TEST_DB["db_name"]

        # Check if db_creds exists and update
        db_creds_result = conn.execute(
            select(DbCreds.db_creds).where(DbCreds.db_name == db_name)
        ).fetchone()


#         if db_creds_result:
#             conn.execute(
#                 update(DbCreds)
#                 .where(DbCreds.db_name == db_name)
#                 .values(
#                     db_creds=TEST_DB["db_creds"],
#                     db_type=TEST_DB["db_type"],
#                 )
#             )
#             print(f"DbCreds for db_name={db_name} updated.")
#         else:
#             conn.execute(
#                 insert(DbCreds).values(
#                     db_name=db_name,
#                     db_creds=TEST_DB["db_creds"],
#                     db_type=TEST_DB["db_type"],
#                 )
#             )
#             print(f"DbCreds for db_name={db_name} created.")


@pytest.fixture
def admin_token():
    """Get admin token for authentication"""
    response = requests.post(
        f"{BASE_URL}/login", json={"username": USERNAME, "password": PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    return data["token"]


def test_admin_login(admin_token):
    """Test admin login functionality"""
    assert admin_token is not None


def test_add_db_creds(admin_token):
    # updates db_creds in the system for a db_name

    """Test adding a new database with real Postgres connection"""
    try:
        # First setup the test database in our system
        # setup_test_database()

        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Prepare database credentials
        payload = {
            "token": admin_token,  # Token must be in the request body
            "db_name": db_name,
            "db_type": TEST_DB["db_type"],
            "db_creds": TEST_DB["db_creds"],
        }

        print(
            "\nSending update_db_creds request with payload:",
            json.dumps(payload, indent=2),
        )

        # Add the database
        response = requests.post(
            f"{BASE_URL}/integration/update_db_creds", json=payload
        )

        print("\nupdate_db_creds response:", response.status_code)
        print(response.text)

        # Check response
        assert (
            response.status_code == 200
        ), f"Failed to add database. Response: {response.text}"
        data = response.json()
        assert data.get("success") is True

        # Prepare get_tables request
        get_tables_payload = {"token": admin_token, "db_name": db_name}

        print(
            "\nSending get_tables_db_creds request with payload:",
            json.dumps(get_tables_payload, indent=2),
        )

        # Verify database was added by trying to get its credentials
        response = requests.post(
            f"{BASE_URL}/integration/get_tables_db_creds", json=get_tables_payload
        )

        print("\nget_tables_db_creds response:", response.status_code)
        print(response.text)

        assert (
            response.status_code == 200
        ), f"Failed to get database tables. Response: {response.text}"
        data = response.json()
        assert "error" not in data, f"Error in response: {data.get('error')}"

        # Verify we got our real tables back
        tables = data.get("tables", [])
        assert "users" in tables, "Users table not found"
        assert "orders" in tables, "Orders table not found"

        # Verify credentials were returned correctly
        assert data.get("db_type") == "postgres"
        assert "db_creds" in data
        db_creds = data["db_creds"]
        assert db_creds.get("port") == 5432
        assert db_creds.get("database") == "test_db"
        assert db_creds.get("user") == "postgres"
        assert db_creds.get("password") == "postgres"
        assert db_creds.get("host") == "host.docker.internal"

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise


def test_add_metadata(admin_token):
    """Test adding metadata for a database"""
    try:
        # First setup the test database in our system
        # setup_test_database()

        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Create metadata list
        metadata = [
            {
                "table_name": "users",
                "column_name": "id",
                "data_type": "integer",
                "column_description": "Unique identifier for users",
                "is_primary_key": True,
                "is_foreign_key": False,
                "foreign_key_table": None,
                "foreign_key_column": None,
            },
            {
                "table_name": "users",
                "column_name": "name",
                "data_type": "varchar",
                "column_description": "Name of the user",
                "is_primary_key": False,
                "is_foreign_key": False,
                "foreign_key_table": None,
                "foreign_key_column": None,
            },
            {
                "table_name": "orders",
                "column_name": "id",
                "data_type": "integer",
                "column_description": "Unique identifier for orders",
                "is_primary_key": True,
                "is_foreign_key": False,
                "foreign_key_table": None,
                "foreign_key_column": None,
            },
            {
                "table_name": "orders",
                "column_name": "user_id",
                "data_type": "integer",
                "column_description": "Reference to users table",
                "is_primary_key": False,
                "is_foreign_key": True,
                "foreign_key_table": "users",
                "foreign_key_column": "id",
            },
            {
                "table_name": "orders",
                "column_name": "amount",
                "data_type": "decimal",
                "column_description": "Order amount",
                "is_primary_key": False,
                "is_foreign_key": False,
                "foreign_key_table": None,
                "foreign_key_column": None,
            },
        ]

        # Make request to update metadata
        response = requests.post(
            f"{BASE_URL}/integration/update_metadata",
            json={"token": admin_token, "db_name": db_name, "metadata": metadata},
        )

        # Check update response
        assert (
            response.status_code == 200
        ), f"Failed to update metadata: {response.text}"
        data = response.json()
        assert data["success"] == True

        # Now fetch the metadata and verify it
        get_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
        )

        assert (
            get_response.status_code == 200
        ), f"Failed to get metadata: {get_response.text}"
        get_data = get_response.json()
        fetched_metadata = get_data["metadata"]

        # Debug print to see structure
        print("\nFetched metadata structure:")
        print(json.dumps(fetched_metadata[0], indent=2))

        # Verify each piece of metadata was stored correctly
        for expected_meta in metadata:
            matching_meta = next(
                (
                    m
                    for m in fetched_metadata
                    if m["table_name"] == expected_meta["table_name"]
                    and m["column_name"] == expected_meta["column_name"]
                ),
                None,
            )
            assert (
                matching_meta is not None
            ), f"Could not find metadata for {expected_meta['table_name']}.{expected_meta['column_name']}"

            # Verify the fields that are returned by the API
            for key in ["table_name", "column_name", "data_type", "column_description"]:
                assert matching_meta[key] == expected_meta[key], (
                    f"Mismatch in {key} for {expected_meta['table_name']}.{expected_meta['column_name']}: "
                    f"expected {expected_meta[key]}, got {matching_meta[key]}"
                )

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_add_instructions(admin_token):
    """Test adding and retrieving instructions for a database"""
    try:
        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Create test instructions
        test_instructions = """
        Here are some important notes about the database:
        1. The users table contains basic user information
        2. The orders table tracks all orders made by users
        3. Each order must be associated with a valid user_id
        4. Order amounts are stored in decimal format
        """.strip()

        # Update instructions
        response = requests.post(
            f"{BASE_URL}/integration/update_instructions",
            json={
                "token": admin_token,
                "db_name": db_name,
                "instructions": test_instructions,
            },
            headers={"Content-Type": "application/json"},
        )

        # Check update response
        assert (
            response.status_code == 200
        ), f"Failed to update instructions: {response.text}"
        data = response.json()
        assert data["success"] == True

        # Now fetch the instructions and verify
        get_response = requests.post(
            f"{BASE_URL}/integration/get_instructions",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )

        assert (
            get_response.status_code == 200
        ), f"Failed to get instructions: {get_response.text}"
        get_data = get_response.json()
        fetched_instructions = get_data["instructions"]

        # Verify instructions match
        assert (
            fetched_instructions == test_instructions
        ), f"Instructions mismatch. Expected:\n{test_instructions}\n\nGot:\n{fetched_instructions}"

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_add_golden_queries(admin_token):
    """Test adding and retrieving golden queries for a database"""
    try:
        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Create test golden queries
        test_golden_queries = [
            {
                "question": "Show me all users who have placed orders",
                "sql": "SELECT DISTINCT u.name FROM users u JOIN orders o ON u.id = o.user_id;",
            },
            {
                "question": "What is the total amount of orders for each user?",
                "sql": "SELECT u.name, SUM(o.amount) as total_amount FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name;",
            },
        ]

        # Update golden queries
        response = requests.post(
            f"{BASE_URL}/integration/update_golden_queries",
            json={
                "token": admin_token,
                "db_name": db_name,
                "golden_queries": test_golden_queries,
            },
            headers={"Content-Type": "application/json"},
        )

        # Check update response
        assert (
            response.status_code == 200
        ), f"Failed to update golden queries: {response.text}"
        data = response.json()
        assert data["success"] == True

        # Now fetch the golden queries and verify
        get_response = requests.post(
            f"{BASE_URL}/integration/get_golden_queries",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )

        assert (
            get_response.status_code == 200
        ), f"Failed to get golden queries: {get_response.text}"
        get_data = get_response.json()
        fetched_queries = get_data["golden_queries"]

        # Verify golden queries match
        assert len(fetched_queries) == len(
            test_golden_queries
        ), f"Number of golden queries mismatch. Expected {len(test_golden_queries)}, got {len(fetched_queries)}"

        # Sort both lists by question to ensure consistent comparison
        test_golden_queries.sort(key=lambda x: x["question"])
        fetched_queries.sort(key=lambda x: x["question"])

        for test_query, fetched_query in zip(test_golden_queries, fetched_queries):
            assert (
                test_query["question"] == fetched_query["question"]
            ), f"Question mismatch. Expected: {test_query['question']}, Got: {fetched_query['question']}"
            assert (
                test_query["sql"] == fetched_query["sql"]
            ), f"SQL mismatch for question '{test_query['question']}'. Expected: {test_query['sql']}, Got: {fetched_query['sql']}"
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


# TODO: add case for google sheets url and single user and a single user with token
def test_add_users(admin_token):
    """Test adding and updating users via the admin API"""
    try:
        # Create test users CSV content
        test_users_csv = "username,password\ntest.user1@example.com,testpass1\ntest.user2@example.com,testpass2"

        # Add users
        response = requests.post(
            f"{BASE_URL}/admin/add_users",
            json={"token": admin_token, "users_csv": test_users_csv},
            headers={"Content-Type": "application/json"},
        )

        # Check response
        assert response.status_code == 200, f"Failed to add users: {response.text}"

        # Get users to verify they were added
        get_response = requests.post(
            f"{BASE_URL}/admin/get_users",
            json={"token": admin_token},
            headers={"Content-Type": "application/json"},
        )

        assert (
            get_response.status_code == 200
        ), f"Failed to get users: {get_response.text}"
        users_data = get_response.json()
        users = users_data["users"]

        # Verify both test users exist
        user_emails = [user["username"] for user in users]
        assert (
            "test.user1@example.com" in user_emails
        ), "test.user1 not found in users list"
        assert (
            "test.user2@example.com" in user_emails
        ), "test.user2 not found in users list"

        # Test updating an existing user with new password
        update_users_csv = "username,password\ntest.user1@example.com,newpass1"

        update_response = requests.post(
            f"{BASE_URL}/admin/add_users",
            json={"token": admin_token, "users_csv": update_users_csv},
            headers={"Content-Type": "application/json"},
        )

        assert (
            update_response.status_code == 200
        ), f"Failed to update user: {update_response.text}"

        # Clean up - delete test users
        for username in ["test.user1@example.com", "test.user2@example.com"]:
            delete_response = requests.post(
                f"{BASE_URL}/admin/delete_user",
                json={"token": admin_token, "username": username},
                headers={"Content-Type": "application/json"},
            )
            assert (
                delete_response.status_code == 200
            ), f"Failed to delete user {username}: {delete_response.text}"

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_generate_query(admin_token):
    """Test SQL query generation"""
    try:
        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Generate a SQL query
        question = "Show me all users"
        generate_response = requests.post(
            f"{BASE_URL}/generate_sql_query",
            json={
                "token": admin_token,
                "db_name": db_name,
                "question": question,
            },
            headers={"Content-Type": "application/json"},
        )

        assert (
            generate_response.status_code == 200
        ), f"Failed to generate SQL: {generate_response.text}"
        generate_data = generate_response.json()
        assert "sql" in generate_data, "No SQL in response"
        assert (
            generate_data["error"] is None
        ), f"Error in SQL generation: {generate_data['error']}"

        sql = generate_data["sql"]
        print(f"\nGenerated SQL: {sql}")

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_run_query(admin_token):
    """Test getting first row from users table"""
    from utils_sql import execute_sql
    import asyncio
    
    # Database credentials
    db_creds = {
        "host": "host.docker.internal",
        "port": 5432,
        "database": "test_db",
        "user": "postgres",
        "password": "postgres",
    }
    
    # Query to get first row from users table
    sql = "SELECT * FROM users LIMIT 1;"

    # Execute query
    df, err = asyncio.run(execute_sql("postgres", db_creds, sql))
    
    # Assert no errors
    assert err is None, f"Error executing query: {err}"
    
    # Assert we got a dataframe with one row
    assert df is not None, "No dataframe returned"
    assert len(df) == 1, f"Expected 1 row, got {len(df)}"
    
    # Assert all expected columns are present
    expected_columns = ["id", "name", "email", "created_at"]
    assert all(col in df.columns for col in expected_columns), f"Missing columns. Expected {expected_columns}, got {df.columns.tolist()}"
    
    # Print the result
    print("First user in database:")
    print(df.to_dict(orient="records")[0])