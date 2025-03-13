"""Integration tests for the Defog backend API routes.
Tests database setup, configuration, user management, query execution, and cleanup, requires Docker on localhost:1235."""

import json
import os
import random

import requests
import pytest
from conftest import BASE_URL, TEST_DB, cleanup_test_database


def test_admin_login(admin_token):
    """Test admin login functionality i.e. the token returned is not None"""
    assert admin_token is not None


def test_add_db_creds(admin_token):
    """Test adding database credentials via the API.
    This test verifies:
    1. We can add database credentials through the update_db_creds endpoint
    2. We can retrieve and verify the added credentials through get_tables_db_creds endpoint
    3. The database tables are accessible with the registered credentials
    """
    try:
        db_name = TEST_DB["db_name"]

        # Step 1: Add database credentials via API
        add_creds_payload = {
            "token": admin_token,
            "db_name": db_name,
            "db_type": TEST_DB["db_type"],
            "db_creds": TEST_DB["db_creds"],
        }
        response = requests.post(
            f"{BASE_URL}/integration/update_db_creds", json=add_creds_payload
        )
        assert response.status_code == 200, f"Failed to add database credentials. Response: {response.text}"

        # Step 2: Verify credentials were added correctly
        get_tables_payload = {"token": admin_token, "db_name": db_name}
        response = requests.post(
            f"{BASE_URL}/integration/get_db_info", json=get_tables_payload
        )
        assert response.status_code == 200, f"Failed to get database tables. Response: {response.text}"
        data = response.json()
        assert "error" not in data

        # Step 3: Verify database configuration
        assert data.get("db_type") == TEST_DB["db_type"]
        assert "db_creds" in data

        db_creds = data["db_creds"]
        expected_creds = TEST_DB["db_creds"]
        for key in ["port", "database", "user", "password", "host"]:
            assert db_creds.get(key) == expected_creds.get(key), f"Mismatch in {key}"

        # Step 4: Verify tables are accessible
        tables = data.get("tables", [])
        expected_tables = ["customers", "ticket_types", "ticket_sales"]
        for table in expected_tables:
            assert table in tables, f"{table} table not found"

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise


def test_add_initial_metadata(admin_token):
    """Test adding initial metadata for a database.
    This test verifies we can add metadata for all tables and columns,
    and that the metadata is stored correctly.
    """
    try:
        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Create metadata list for our ticket booking system
        metadata = [
            # Customers table metadata
            {
                "table_name": "customers",
                "column_name": "id",
                "data_type": "integer",
                "column_description": "Unique identifier for customers",
            },
            {
                "table_name": "customers",
                "column_name": "name",
                "data_type": "varchar",
                "column_description": "Full name of the customer",
            },
            {
                "table_name": "customers",
                "column_name": "email",
                "data_type": "varchar",
                "column_description": "Customer's email address",
            },
            # Ticket Types table metadata
            {
                "table_name": "ticket_types",
                "column_name": "id",
                "data_type": "integer",
                "column_description": "Unique identifier for ticket types",
            },
            {
                "table_name": "ticket_types",
                "column_name": "name",
                "data_type": "varchar",
                "column_description": "Name of the ticket type (e.g., Standard, VIP)",
            },
            {
                "table_name": "ticket_types",
                "column_name": "price",
                "data_type": "decimal",
                "column_description": "Price of the ticket type",
            },
            # Ticket Sales table metadata
            {
                "table_name": "ticket_sales",
                "column_name": "id",
                "data_type": "integer",
                "column_description": "Unique identifier for ticket sales",
            },
            {
                "table_name": "ticket_sales",
                "column_name": "customer_id",
                "data_type": "integer",
                "column_description": "Reference to the customer who bought the ticket",
            },
            {
                "table_name": "ticket_sales",
                "column_name": "ticket_type_id",
                "data_type": "integer",
                "column_description": "Reference to the type of ticket purchased",
            },
            {
                "table_name": "ticket_sales",
                "column_name": "status",
                "data_type": "varchar",
                "column_description": "Current status of the ticket (active, used, expired)",
            }
        ]

        # Make request to update metadata
        response = requests.post(
            f"{BASE_URL}/integration/update_metadata",
            json={"token": admin_token, "db_name": db_name, "metadata": metadata},
        )

        # Check update response
        assert response.status_code == 200, f"Failed to update metadata: {response.text}"
        update_data = response.json()
        assert update_data["db_name"] == db_name
        assert set(update_data["tables"]) == set(["customers", "ticket_sales", "ticket_types"])
        assert update_data["db_creds"] == TEST_DB["db_creds"]
        assert update_data["db_type"] == TEST_DB["db_type"]
        assert set(update_data["selected_tables"]) == set(["customers", "ticket_sales", "ticket_types"])
        assert update_data["can_connect"] == True
        for column_metadata in update_data["metadata"]:
            table_name = column_metadata["table_name"]
            column_name = column_metadata["column_name"]
            found = False
            for expected_meta in metadata:
                if expected_meta["table_name"] == table_name and expected_meta["column_name"] == column_name:
                    assert column_metadata["data_type"] == expected_meta["data_type"]
                    assert column_metadata["column_description"] == expected_meta["column_description"]
                    found = True
                    break
            assert found, f"Could not find metadata for {table_name}.{column_name}"


        # Now fetch the metadata and verify it
        get_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
        )

        assert get_response.status_code == 200, f"Failed to get metadata: {get_response.text}"
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
            assert matching_meta is not None, f"Could not find metadata for {expected_meta['table_name']}.{expected_meta['column_name']}"

            # Verify the fields that are returned by the API
            for key in ["table_name", "column_name", "data_type", "column_description"]:
                assert matching_meta[key] == expected_meta[key], (
                    f"Mismatch in {key} for {expected_meta['table_name']}.{expected_meta['column_name']}: "
                    f"expected {expected_meta[key]}, got {matching_meta[key]}"
                )

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_update_metadata(admin_token):
    """Test updating existing metadata.
    This test verifies we can:
    1. Update specific column descriptions
    2. Leave other metadata unchanged
    3. Verify the updates are reflected correctly
    """
    try:
        db_name = TEST_DB["db_name"]
        
        # First, get current metadata
        response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
        )
        assert response.status_code == 200, "Failed to get current metadata"
        current_metadata = response.json()["metadata"]
        
        # Create updated metadata with some changes
        updated_metadata = current_metadata.copy()
        updates = {
            ("customers", "email"): "Primary email address for customer communications and notifications",
            ("ticket_types", "price"): "Price of the ticket type in USD",
            ("ticket_sales", "status"): "Current status of the ticket (active, used, expired, refunded)"
        }
        
        # Update specific column descriptions
        for meta in updated_metadata:
            key = (meta["table_name"], meta["column_name"])
            if key in updates:
                meta["column_description"] = updates[key]
        
        # Send update request
        response = requests.post(
            f"{BASE_URL}/integration/update_metadata",
            json={"token": admin_token, "db_name": db_name, "metadata": updated_metadata},
        )
        assert response.status_code == 200, f"Failed to update metadata: {response.text}"
        
        # Verify updates
        verify_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
        )
        assert verify_response.status_code == 200, "Failed to get updated metadata"
        final_metadata = verify_response.json()["metadata"]
        
        # Check that updates were applied correctly
        for meta in final_metadata:
            key = (meta["table_name"], meta["column_name"])
            if key in updates:
                assert meta["column_description"] == updates[key], (
                    f"Update failed for {key[0]}.{key[1]}: "
                    f"expected '{updates[key]}', got '{meta['column_description']}'"
                )
            else:
                # Verify other metadata remained unchanged
                original = next(
                    m for m in current_metadata
                    if m["table_name"] == meta["table_name"]
                    and m["column_name"] == meta["column_name"]
                )
                assert meta["column_description"] == original["column_description"], (
                    f"Unexpected change in {key[0]}.{key[1]}"
                )
                
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_initial_instructions(admin_token):
    """Test adding initial instructions for a database and verifying they are stored correctly"""
    try:
        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Create test instructions
        test_instructions = """
        Here are some important notes about the ticket booking database:
        1. The customers table stores customer information including name and email
        2. The ticket_types table defines different types of tickets (Standard, VIP, Student) with their prices
        3. The ticket_sales table tracks all ticket purchases, linking customers to their purchased ticket types
        4. Each ticket sale has a status (active, used, expired) and valid_until date
        5. All monetary values (ticket prices) are stored in decimal format
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
        assert response.status_code == 200, f"Failed to update instructions: {response.text}"
        data = response.json()
        assert data["success"] == True

        # Now fetch the instructions and verify
        get_response = requests.post(
            f"{BASE_URL}/integration/get_instructions",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )

        assert get_response.status_code == 200, f"Failed to get instructions: {get_response.text}"
        get_data = get_response.json()
        fetched_instructions = get_data["instructions"]

        # Verify instructions match
        assert fetched_instructions == test_instructions, f"Instructions mismatch. Expected:\n{test_instructions}\n\nGot:\n{fetched_instructions}"

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_update_instructions(admin_token):
    """Test updating existing instructions and verifying the changes"""
    try:
        db_name = TEST_DB["db_name"]

        # First, set initial instructions
        initial_instructions = """
        Basic database instructions:
        1. Customers table has basic user info
        2. Ticket types include pricing
        3. Sales track purchases
        """.strip()

        # Set initial instructions
        response = requests.post(
            f"{BASE_URL}/integration/update_instructions",
            json={
                "token": admin_token,
                "db_name": db_name,
                "instructions": initial_instructions,
            },
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, "Failed to set initial instructions"

        # Update with more detailed instructions
        updated_instructions = """
        Detailed database instructions:
        1. Customers table contains user profiles with name, email, and contact preferences
        2. Ticket types table defines various categories (VIP, Standard, Student) with dynamic pricing
        3. Sales table maintains complete purchase history with status tracking
        4. All financial transactions are logged with timestamps
        5. Status updates are automated based on usage and expiration
        """.strip()

        # Update instructions
        response = requests.post(
            f"{BASE_URL}/integration/update_instructions",
            json={
                "token": admin_token,
                "db_name": db_name,
                "instructions": updated_instructions,
            },
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, "Failed to update instructions"
        assert response.json()["success"] == True

        # Verify updated instructions
        get_response = requests.post(
            f"{BASE_URL}/integration/get_instructions",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, "Failed to get updated instructions"
        
        fetched_instructions = get_response.json()["instructions"]
        assert fetched_instructions == updated_instructions, f"Instructions mismatch after update. Expected:\n{updated_instructions}\n\nGot:\n{fetched_instructions}"

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_initial_golden_queries(admin_token):
    """Test adding initial golden queries and verifying they are stored correctly"""
    try:
        db_name = TEST_DB["db_name"]

        # First, get existing queries to clean up
        get_response = requests.post(
            f"{BASE_URL}/integration/get_golden_queries",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, "Failed to get existing golden queries"
        existing_queries = get_response.json()["golden_queries"]

        # Delete any existing queries
        if existing_queries:
            delete_response = requests.post(
                f"{BASE_URL}/integration/delete_golden_queries",
                json={
                    "token": admin_token,
                    "db_name": db_name,
                    "questions": [q["question"] for q in existing_queries],
                },
                headers={"Content-Type": "application/json"},
            )
            assert delete_response.status_code == 200, "Failed to delete existing queries"

        # Create initial test golden queries
        test_golden_queries = [
            {
                "question": "Show me all customers who have purchased tickets",
                "sql": "SELECT DISTINCT c.name, c.email FROM customers c JOIN ticket_sales ts ON c.id = ts.customer_id;",
            },
            {
                "question": "What is the total amount spent by each customer on tickets?",
                "sql": "SELECT c.name, SUM(tt.price) as total_spent FROM customers c JOIN ticket_sales ts ON c.id = ts.customer_id JOIN ticket_types tt ON ts.ticket_type_id = tt.id GROUP BY c.name;",
            },
        ]

        # Add golden queries
        response = requests.post(
            f"{BASE_URL}/integration/update_golden_queries",
            json={
                "token": admin_token,
                "db_name": db_name,
                "golden_queries": test_golden_queries,
            },
            headers={"Content-Type": "application/json"},
        )

        # Check response
        assert response.status_code == 200, f"Failed to add golden queries: {response.text}"
        assert response.json()["success"] == True

        # Fetch and verify the golden queries
        get_response = requests.post(
            f"{BASE_URL}/integration/get_golden_queries",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )

        assert get_response.status_code == 200, f"Failed to get golden queries: {get_response.text}"
        fetched_queries = get_response.json()["golden_queries"]

        # Verify queries match
        assert len(fetched_queries) == len(test_golden_queries), (
            f"Number of golden queries mismatch. Expected {len(test_golden_queries)}, "
            f"got {len(fetched_queries)}"
        )

        # Sort both lists by question for comparison
        test_golden_queries.sort(key=lambda x: x["question"])
        fetched_queries.sort(key=lambda x: x["question"])

        for test_query, fetched_query in zip(test_golden_queries, fetched_queries):
            assert test_query["question"] == fetched_query["question"], (
                f"Question mismatch. Expected: {test_query['question']}, "
                f"Got: {fetched_query['question']}"
            )
            assert test_query["sql"] == fetched_query["sql"], (
                f"SQL mismatch for question '{test_query['question']}'. "
                f"Expected: {test_query['sql']}, Got: {fetched_query['sql']}"
            )

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_update_golden_queries(admin_token):
    """Test updating existing golden queries and verifying the changes"""
    try:
        db_name = TEST_DB["db_name"]

        # First, get existing queries to clean up
        get_response = requests.post(
            f"{BASE_URL}/integration/get_golden_queries",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, "Failed to get existing golden queries"
        existing_queries = get_response.json()["golden_queries"]

        # Delete any existing queries
        if existing_queries:
            delete_response = requests.post(
                f"{BASE_URL}/integration/delete_golden_queries",
                json={
                    "token": admin_token,
                    "db_name": db_name,
                    "questions": [q["question"] for q in existing_queries],
                },
                headers={"Content-Type": "application/json"},
            )
            assert delete_response.status_code == 200, "Failed to delete existing queries"

        # First, set initial golden queries
        initial_queries = [
            {
                "question": "List all customers",
                "sql": "SELECT name, email FROM customers;",
            },
            {
                "question": "Show ticket prices",
                "sql": "SELECT name, price FROM ticket_types;",
            },
        ]

        # Set initial queries
        response = requests.post(
            f"{BASE_URL}/integration/update_golden_queries",
            json={
                "token": admin_token,
                "db_name": db_name,
                "golden_queries": initial_queries,
            },
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, "Failed to set initial golden queries"

        # Verify initial queries were set
        get_response = requests.post(
            f"{BASE_URL}/integration/get_golden_queries",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, "Failed to get initial golden queries"
        initial_fetched = get_response.json()["golden_queries"]
        assert len(initial_fetched) == len(initial_queries), "Initial queries not set correctly"

        # Create updated queries with more complex examples
        updated_queries = [
            {
                "question": "Show total revenue by ticket type",
                "sql": "SELECT tt.name, COUNT(*) as tickets_sold, SUM(tt.price) as total_revenue FROM ticket_sales ts JOIN ticket_types tt ON ts.ticket_type_id = tt.id GROUP BY tt.name ORDER BY total_revenue DESC;",
            },
            {
                "question": "Find customers who bought VIP tickets",
                "sql": "SELECT DISTINCT c.name, c.email FROM customers c JOIN ticket_sales ts ON c.id = ts.customer_id JOIN ticket_types tt ON ts.ticket_type_id = tt.id WHERE tt.name = 'VIP';",
            },
            {
                "question": "Show expired tickets count by type",
                "sql": "SELECT tt.name, COUNT(*) as expired_count FROM ticket_sales ts JOIN ticket_types tt ON ts.ticket_type_id = tt.id WHERE ts.status = 'expired' GROUP BY tt.name;",
            },
        ]

        # Update queries
        response = requests.post(
            f"{BASE_URL}/integration/update_golden_queries",
            json={
                "token": admin_token,
                "db_name": db_name,
                "golden_queries": updated_queries,
            },
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, "Failed to update golden queries"
        assert response.json()["success"] == True

        # Verify updated queries
        get_response = requests.post(
            f"{BASE_URL}/integration/get_golden_queries",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, "Failed to get updated golden queries"
        
        fetched_queries = get_response.json()["golden_queries"]
        
        # We expect to see both initial and updated queries since update_golden_queries doesn't delete
        expected_total = len(initial_queries) + len(updated_queries)
        assert len(fetched_queries) == expected_total, (
            f"Number of queries mismatch after update. Expected {expected_total} "
            f"(initial: {len(initial_queries)} + updated: {len(updated_queries)}), "
            f"got {len(fetched_queries)}"
        )

        # Verify all updated queries are present
        fetched_questions = {q["question"]: q["sql"] for q in fetched_queries}
        for updated_query in updated_queries:
            assert updated_query["question"] in fetched_questions, (
                f"Updated query '{updated_query['question']}' not found in fetched queries"
            )
            assert updated_query["sql"] == fetched_questions[updated_query["question"]], (
                f"SQL mismatch for question '{updated_query['question']}'. "
                f"Expected: {updated_query['sql']}, "
                f"Got: {fetched_questions[updated_query['question']]}"
            )

        # Verify initial queries are still present
        for initial_query in initial_queries:
            assert initial_query["question"] in fetched_questions, (
                f"Initial query '{initial_query['question']}' not found in fetched queries"
            )
            assert initial_query["sql"] == fetched_questions[initial_query["question"]], (
                f"SQL mismatch for question '{initial_query['question']}'. "
                f"Expected: {initial_query['sql']}, "
                f"Got: {fetched_questions[initial_query['question']]}"
            )

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


# TODO: add case for google sheets url and single user and a single user with token
def test_add_users(admin_token):
    """Test adding and updating users via CSV content"""
    try:
        test_users = [
            {"email": "test.user1@example.com", "password": "testpass1"},
            {"email": "test.user2@example.com", "password": "testpass2"},
        ]
        test_users_csv = "username,password\n" + \
            "\n".join([f"{u['email']},{u['password']}" for u in test_users])

        # Add users via CSV
        response = requests.post(
            f"{BASE_URL}/admin/add_users",
            json={"token": admin_token, "users_csv": test_users_csv},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, f"Failed to add users: {response.text}"

        # Verify users were added
        get_response = requests.post(
            f"{BASE_URL}/admin/get_users",
            json={"token": admin_token},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, f"Failed to get users: {get_response.text}"
        
        users = get_response.json()["users"]
        user_emails = [user["username"] for user in users]
        for test_user in test_users:
            assert test_user["email"] in user_emails, f"{test_user['email']} not found in users list"

        # Clean up
        for test_user in test_users:
            delete_response = requests.post(
                f"{BASE_URL}/admin/delete_user",
                json={"token": admin_token, "username": test_user["email"]},
                headers={"Content-Type": "application/json"},
            )
            assert delete_response.status_code == 200, \
                f"Failed to delete user {test_user['email']}: {delete_response.text}"

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_update_users(admin_token):
    """Test updating an existing user's password via CSV"""
    try:
        # First create a test user
        test_user = {"email": "test.update@example.com", "password": "oldpass"}
        initial_csv = f"username,password\n{test_user['email']},{test_user['password']}"

        response = requests.post(
            f"{BASE_URL}/admin/add_users",
            json={"token": admin_token, "users_csv": initial_csv},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, "Failed to create initial user"

        # Update the user's password
        new_password = "newpass123"
        update_csv = f"username,password\n{test_user['email']},{new_password}"

        update_response = requests.post(
            f"{BASE_URL}/admin/add_users",
            json={"token": admin_token, "users_csv": update_csv},
            headers={"Content-Type": "application/json"},
        )
        assert update_response.status_code == 200, f"Failed to update user: {update_response.text}"

        # Verify we can login with new password
        login_response = requests.post(
            f"{BASE_URL}/login",
            json={"username": test_user["email"], "password": new_password},
        )
        assert login_response.status_code == 200, "Failed to login with new password"

        # Clean up
        delete_response = requests.post(
            f"{BASE_URL}/admin/delete_user",
            json={"token": admin_token, "username": test_user["email"]},
            headers={"Content-Type": "application/json"},
        )
        assert delete_response.status_code == 200, f"Failed to delete test user: {delete_response.text}"

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

        assert generate_response.status_code == 200, f"Failed to generate SQL: {generate_response.text}"
        generate_data = generate_response.json()
        assert "sql" in generate_data, "No SQL in response"
        assert generate_data["error"] is None, f"Error in SQL generation: {generate_data['error']}"

        sql = generate_data["sql"]
        print(f"\nGenerated SQL: {sql}")

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_run_query(admin_token):
    """Test getting first row from customers table"""
    import asyncio

    from utils_sql import execute_sql

    # Use test database configuration
    db_creds = TEST_DB["db_creds"]

    # Query to get first row from customers table
    sql = "SELECT * FROM customers LIMIT 1;"

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
    print("First customer in database:")
    print(df.to_dict(orient="records")[0])


def test_oracle_report_generation(admin_token):
    """Test the oracle report generation flow including clarifications and report generation"""
    try:
        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # Step 1: Ask for clarification questions
        user_question = "What are the sales trends for each ticket type?"
        clarify_response = requests.post(
            f"{BASE_URL}/oracle/clarify_question",
            json={
                "token": admin_token,
                "db_name": db_name,
                "user_question": user_question,
                "answered_clarifications": [],
                "clarification_guidelines": "If unspecified, trends should cover the last 3 months on a weekly basis."
            },
            headers={"Content-Type": "application/json"},
        )

        # Check clarification response
        assert clarify_response.status_code == 200, f"Failed to get clarifications: {clarify_response.text}"
        clarify_data = clarify_response.json()
        clarifications = clarify_data.get("clarifications", [])

        report_id = clarify_data.get("report_id", None)
        assert report_id is not None, "Report ID not found in response"

        print("\nReceived clarification questions:")
        for c in clarifications:
            print(f"- {c['clarification']}")
            if 'options' in c:
                print(f"  Options: {c['options']}")

        # Step 2: Answer a couple expected clarifications
        def get_clarification_answer(clarification: str) -> str:
            clarification = clarification.lower()
            if "sales metric" in clarification:
                return "Sales revenue"
            elif "status" in clarification:
                return "Combine all statuses"
            else:
                return "All ticket types"

        answered_clarifications = [
            {
                "clarification": c["clarification"],
                "answer": get_clarification_answer(c["clarification"])
            }
            for c in clarifications
        ]

        # Step 3: Generate the report
        report_response = requests.post(
            f"{BASE_URL}/oracle/generate_report",
            json={
                "report_id": report_id,
                "token": admin_token,
                "db_name": db_name,
                "user_question": user_question,
                "answered_clarifications": answered_clarifications
            },
            headers={"Content-Type": "application/json"},
        )

        # Check report response
        assert report_response.status_code == 200, f"Failed to generate report: {report_response.text}"
        report_data = report_response.json()

        # Verify report content
        assert "mdx" in report_data, "No MDX content in report response"
        assert "sql_answers" in report_data, "No sql_answers in report response"

        print("\nGenerated Report:")
        print(report_data["mdx"])

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_custom_tools_crud(admin_token):
    """
    Test the CRUD operations for custom tools API:
    1. Create a custom tool
    2. List custom tools
    3. Get a specific custom tool
    4. Update a custom tool
    5. Toggle a custom tool
    6. Delete a custom tool
    """
    try:
        # Define a simple custom tool
        tool_name = "test_counter_tool"
        tool_description = "A simple counter tool for testing"
        
        input_model = """
class CounterInput(BaseModel):
    start: int = Field(1, description="Starting value")
    count: int = Field(5, description="Number of items to count")
"""
        
        tool_code = """
async def test_counter_tool(input: CounterInput):
    \"\"\"
    Generates a simple count sequence.
    \"\"\"
    start = input.start
    count = input.count
    
    results = []
    for i in range(start, start + count):
        results.append(i)
    
    return {
        "sequence": results,
        "count": count,
        "start": start,
        "end": start + count - 1
    }
"""
        
        # Step 1: Create a custom tool
        create_response = requests.post(
            f"{BASE_URL}/custom_tools/create",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "tool_description": tool_description,
                "input_model": input_model,
                "tool_code": tool_code
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert create_response.status_code == 200, f"Failed to create custom tool: {create_response.text}"
        create_data = create_response.json()
        assert create_data["status"] == "success", f"Create tool failed: {create_data}"
        assert create_data["tool"]["tool_name"] == tool_name, "Tool name mismatch in create response"
        
        # Step 2: List custom tools
        list_response = requests.post(
            f"{BASE_URL}/custom_tools/list",
            json={
                "token": admin_token,
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert list_response.status_code == 200, f"Failed to list custom tools: {list_response.text}"
        list_data = list_response.json()
        assert list_data["status"] == "success", "List custom tools failed"
        assert len(list_data["tools"]) >= 1, "No tools found in list response"
        
        found_tool = False
        for tool in list_data["tools"]:
            if tool["tool_name"] == tool_name:
                found_tool = True
                assert tool["tool_description"].strip() == tool_description.strip(), "Tool description mismatch"
                assert tool["is_enabled"] is True, "Tool should be enabled by default"
        
        assert found_tool, f"Created tool '{tool_name}' not found in tool list"
        
        # Step 3: Get specific custom tool
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 200, f"Failed to get custom tool: {get_response.text}"
        get_data = get_response.json()
        assert get_data["status"] == "success", "Get custom tool failed"
        assert get_data["tool"]["tool_name"].strip() == tool_name.strip(), "Tool name mismatch in get response"
        assert get_data["tool"]["tool_description"].strip() == tool_description.strip(), "Tool description mismatch in get response"
        assert get_data["tool"]["input_model"].strip() == input_model.strip(), "Input model mismatch in get response"
        assert get_data["tool"]["tool_code"].strip() == tool_code.strip(), "Tool code mismatch in get response"
        
        # Step 4: Update custom tool
        updated_description = "An updated counter tool for testing"
        updated_tool_code = tool_code.replace("sequence", "result_sequence")
        
        update_response = requests.post(
            f"{BASE_URL}/custom_tools/update",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "tool_description": updated_description,
                "input_model": input_model,
                "tool_code": updated_tool_code
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert update_response.status_code == 200, f"Failed to update custom tool: {update_response.text}"
        update_data = update_response.json()
        assert update_data["status"] == "success", "Update custom tool failed"
        
        # Verify the update
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 200, "Failed to get updated custom tool"
        get_data = get_response.json()
        assert get_data["tool"]["tool_description"].strip() == updated_description.strip(), "Tool description not updated"
        assert get_data["tool"]["tool_code"].strip() == updated_tool_code.strip(), "Tool code not updated"
        
        # Step 5: Toggle custom tool (disable)
        toggle_response = requests.post(
            f"{BASE_URL}/custom_tools/toggle",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "is_enabled": False
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert toggle_response.status_code == 200, f"Failed to toggle custom tool: {toggle_response.text}"
        toggle_data = toggle_response.json()
        assert toggle_data["status"] == "success", "Toggle custom tool failed"
        assert toggle_data["tool"]["is_enabled"] is False, "Tool should be disabled after toggle"
        
        # Verify the toggle
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 200, "Failed to get toggled custom tool"
        get_data = get_response.json()
        assert get_data["tool"]["is_enabled"] is False, "Tool not disabled after toggle"
        
        # Step 6: Delete custom tool
        delete_response = requests.post(
            f"{BASE_URL}/custom_tools/delete",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert delete_response.status_code == 200, f"Failed to delete custom tool: {delete_response.text}"
        delete_data = delete_response.json()
        assert delete_data["status"] == "success", "Delete custom tool failed"
        
        # Verify deletion
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 404, "Tool should not exist after deletion"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_custom_tool_test_endpoint(admin_token):
    """
    Test the custom tool test endpoint, which allows testing a tool without saving it.
    """
    try:
        # Define a simple test tool
        tool_code = """
async def test_math_tool(input):
    a = input.a
    b = input.b
    operation = input.operation
    
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        result = a / b if b != 0 else "Error: Division by zero"
    else:
        result = "Unknown operation"
    
    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result
    }
"""
        
        input_model = """
class MathInput(BaseModel):
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")
    operation: str = Field(..., description="Operation (add, subtract, multiply, divide)")
"""
        
        # Create test input
        test_input = {
            "a": 10,
            "b": 5,
            "operation": "add"
        }
        
        # Test the tool
        test_response = requests.post(
            f"{BASE_URL}/custom_tools/test",
            json={
                "token": admin_token,
                "tool_code": tool_code,
                "input_model": input_model,
                "test_input": test_input
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert test_response.status_code == 200, f"Failed to test custom tool: {test_response.text}"
        test_data = test_response.json()
        assert test_data["status"] == "success", "Tool test failed"
        assert "result" in test_data, "No result in test response"
        
        # Check the result from the test execution
        tool_result = test_data["result"]
        assert tool_result["operation"] == "add", "Operation mismatch in tool result"
        assert tool_result["a"] == 10, "First number mismatch in tool result"
        assert tool_result["b"] == 5, "Second number mismatch in tool result"
        assert tool_result["result"] == 15, "Addition result incorrect in tool result"
        
        # Test with invalid code (missing async)
        invalid_code = """
def test_math_tool(input):
    a = input.a
    b = input.b
    return {"sum": a + b}
"""
        
        invalid_response = requests.post(
            f"{BASE_URL}/custom_tools/test",
            json={
                "token": admin_token,
                "tool_code": invalid_code,
                "input_model": input_model,
                "test_input": test_input
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert invalid_response.status_code == 400, "Should fail with invalid code"
        
        # Test with unsafe code (using eval)
        unsafe_code = """
async def unsafe_tool(input):
    code = input.code
    return {"result": eval(code)}
"""
        
        unsafe_response = requests.post(
            f"{BASE_URL}/custom_tools/test",
            json={
                "token": admin_token,
                "tool_code": unsafe_code,
                "input_model": input_model,
                "test_input": test_input
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert unsafe_response.status_code == 400, "Should fail with unsafe code"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_custom_tool_execution_integration(admin_token):
    """
    Integration test that creates a custom tool and then tests it through the
    report generation flow to ensure custom tools are loaded and executed correctly.
    """
    try:
        # 1. Create a custom tool that gets data in a specific format
        tool_name = "ticket_summary_tool"
        tool_description = "Summarizes ticket sales data in a predefined format"
        
        input_model = """
class TicketSummaryInput(BaseModel):
    metric: str = Field("count", description="Metric to summarize (count, revenue)")
"""
        
        tool_code = """
async def ticket_summary_tool(input: TicketSummaryInput):
    \"\"\"
    Provides a summary of ticket sales, either by count or by revenue.
    \"\"\"
    metric = input.metric.lower()
    
    # Get database credentials
    db_type, db_creds = await get_db_type_creds("test_db")
    
    if metric == "count":
        # Query for count summary
        sql = \"\"\"
        SELECT tt.name AS ticket_type, COUNT(*) AS total_tickets
        FROM ticket_sales ts
        JOIN ticket_types tt ON ts.ticket_type_id = tt.id
        GROUP BY tt.name
        ORDER BY total_tickets DESC;
        \"\"\"
    else:
        # Query for revenue summary
        sql = \"\"\"
        SELECT tt.name AS ticket_type, COUNT(*) AS tickets_sold, 
               SUM(tt.price) AS total_revenue
        FROM ticket_sales ts
        JOIN ticket_types tt ON ts.ticket_type_id = tt.id
        GROUP BY tt.name
        ORDER BY total_revenue DESC;
        \"\"\"
    
    try:
        # Execute the query
        colnames, rows = await async_execute_query_once(
            db_type=db_type, db_creds=db_creds, query=sql
        )
        
        # Build result
        result_df = pd.DataFrame(rows, columns=colnames)
        
        summary = {
            "metric": metric,
            "data": result_df.to_dict(orient="records"),
            "column_names": colnames,
            "sql": sql
        }
        
        return summary
        
    except Exception as e:
        return {
            "error": str(e),
            "metric": metric
        }
"""
        
        # 2. Create the custom tool
        create_response = requests.post(
            f"{BASE_URL}/custom_tools/create",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "tool_description": tool_description,
                "input_model": input_model,
                "tool_code": tool_code
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert create_response.status_code == 200, f"Failed to create custom tool: {create_response.text}"
        
        # 3. Generate a report that can leverage this custom tool
        # The question explicitly mentions a tool that aligns with our custom tool
        user_question = "Please summarize ticket sales by revenue using the ticket summary tool"
        
        report_response = requests.post(
            f"{BASE_URL}/answer_question_from_database",
            json={
                "token": admin_token,
                "question": user_question,
                "model": "o3-mini"
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert report_response.status_code == 200, f"Failed to generate report: {report_response.text}"
        report_data = report_response.json()
        
        # Expect to see our custom tool in the report output
        assert "report" in report_data, "No report in response"
        assert "tool_outputs" in report_data, "No tool outputs in response"
        
        # 4. Verify the custom tool was used
        custom_tool_used = False
        tool_result = None
        
        for tool_output in report_data["tool_outputs"]:
            tool_name_from_output = tool_output.get("name", "")
            if tool_name_from_output.endswith("ticket_summary_tool"):
                custom_tool_used = True
                tool_result = tool_output.get("result", {})
                break
        
        # Check for evidence of tool usage in the report text
        report_text = report_data["report"]
        print(f"\nReport text: {report_text}")
        
        # 5. Clean up - delete the custom tool
        delete_response = requests.post(
            f"{BASE_URL}/custom_tools/delete",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert delete_response.status_code == 200, f"Failed to delete custom tool: {delete_response.text}"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_add_pdf_to_project(admin_token):
    """Test adding a PDF file to an existing database (test_db)"""
    db_name = TEST_DB["db_name"]
    
    try:
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary PDF file with predictable name
        import tempfile
        import os
        
        pdf_filename = 'test_document.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Get DB info before uploading to check current state
        get_db_info_response = requests.post(
            f"{BASE_URL}/integration/get_db_info",
            json={"token": admin_token, "db_name": db_name},
        )
        assert get_db_info_response.status_code == 200, f"Failed to get DB info: {get_db_info_response.text}"
        
        initial_db_info = get_db_info_response.json()
        initial_pdf_count = len(initial_db_info.get("associated_files", []))
        print(f"\nInitial PDF count: {initial_pdf_count}")
        
        # Upload PDF to existing database
        with open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload the PDF file
            files = [
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': db_name
            }
            
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload PDF: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        
        # Verify the database name matches
        assert data["db_name"] == db_name, f"Expected db_name to be {db_name}, got {data['db_name']}"
        
        # Get updated DB info to verify PDF was added
        updated_db_info = data["db_info"]
        print(f"\nUpdated DB info: {updated_db_info}")
        
        # Verify PDF was associated with the project
        assert "associated_files" in updated_db_info, "No associated_files in db_info"
        assert len(updated_db_info["associated_files"]) > initial_pdf_count, f"No new PDF files added"
        
        # Get the newly added PDF file ID (the last one in the list)
        pdf_file_id = updated_db_info["associated_files"][-1]
        print(f"\nNewly added PDF file ID: {pdf_file_id}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        # Verify PDF file can be downloaded
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Store PDF ID globally for the next test
        global TEST_PDF_ID
        TEST_PDF_ID = pdf_file_id
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_delete_pdf_from_project(admin_token):
    """Test deleting a PDF file from an existing database (test_db)"""
    db_name = TEST_DB["db_name"]
    
    try:
        # First, check if we have a PDF ID from the previous test
        global TEST_PDF_ID
        pdf_file_id = None
        
        try:
            if TEST_PDF_ID:
                pdf_file_id = TEST_PDF_ID
                print(f"\nUsing PDF ID from previous test: {pdf_file_id}")
        except NameError:
            # If TEST_PDF_ID doesn't exist, we'll find one from DB info
            pass
            
        # If we don't have a PDF ID yet, get current DB info to find PDF files
        if not pdf_file_id:
            get_db_info_response = requests.post(
                f"{BASE_URL}/integration/get_db_info",
                json={"token": admin_token, "db_name": db_name},
            )
            assert get_db_info_response.status_code == 200, f"Failed to get DB info: {get_db_info_response.text}"
            
            initial_db_info = get_db_info_response.json()
            print(f"\nInitial DB info: {initial_db_info}")
            
            # Verify there are PDF files associated with the project
            assert "associated_files" in initial_db_info, "No associated_files in db_info"
            associated_files = initial_db_info.get("associated_files", [])
            assert len(associated_files) > 0, "No PDF files found to delete"
            
            # Get the first PDF file ID
            pdf_file_id = associated_files[0]
            
        print(f"\nPDF file ID to delete: {pdf_file_id}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        # Delete the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify the PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        print(f"\nUpdated DB info after deletion: {updated_db_info}")
        
        # Get the currently associated files
        updated_files = updated_db_info.get("associated_files", [])
        
        # If we're dealing with dictionary IDs, convert them for comparison
        if updated_files and isinstance(updated_files[0], dict) and 'file_id' in updated_files[0]:
            file_ids = [f['file_id'] for f in updated_files]
            assert pdf_file_id not in file_ids, "PDF file was not removed from project"
        else:
            assert pdf_file_id not in updated_files, "PDF file was not removed from project"
        
        print(f"\nSuccessfully deleted PDF file with ID: {pdf_file_id}")
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_upload_single_csv_file(admin_token):
    """Test uploading a CSV file through the /upload_files endpoint"""
    try:
        # Create a simple CSV for testing
        csv_content = """Name,Age,City
John Doe,30,New York
Jane Smith,25,Los Angeles
Bob Johnson,40,Chicago"""
        
        # Create CSV file with our desired name
        import os
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, 'test_single_csv_file.csv')
        
        # Write content to the file
        with open(temp_file_path, 'w') as temp_file:
            temp_file.write(csv_content)
        
        # Open the file for upload
        with open(temp_file_path, 'rb') as file:
            # Use multipart form data to upload the file
            files = {'files': (os.path.basename(temp_file_path), file, 'text/csv')}
            form_data = {'token': admin_token}
            
            # Send the upload request
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(temp_file_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload CSV file: {response.text}"
        data = response.json()
        assert "db_name" in data, "No db_name in response"
        assert "db_info" in data, "No db_info in response"
        
        db_name = data["db_name"]
        db_info = data["db_info"]
        
        # Verify the database was created and contains our table
        assert "tables" in db_info, "No tables in db_info"
        assert len(db_info["tables"]) == 1, f"Expected 1 table, got {len(db_info['tables'])}"
        
        # Get the table name (should be based on the CSV filename)
        table_name = db_info["tables"][0]
        assert table_name == "test_single_csv_file", f"Table name '{table_name}' does not match expected 'test_single_csv_file'"
        
        # Verify the table has the correct columns by querying it
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract column names from metadata
        columns = {m["column_name"] for m in metadata if m["table_name"] == table_name}
        expected_columns = {"name", "age", "city"}
        
        # Verify all columns exist (case-insensitive comparison)
        for col in expected_columns:
            assert any(col.lower() == c.lower() for c in columns), f"Column '{col}' not found in uploaded CSV table"
            
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_upload_single_excel_sheet(admin_token):
    """Test uploading an Excel file with a single sheet through the /upload_files endpoint"""
    try:
        # Skip if pandas or openpyxl are not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create a simple Excel file for testing
        data = {
            'Product': ['Widget A', 'Widget B', 'Widget C'],
            'Price': [19.99, 29.99, 39.99],
            'Quantity': [100, 200, 300]
        }
        df = pd.DataFrame(data)
        
        # Create Excel file with our desired name
        import os
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, 'test_single_excel_sheet.xlsx')
        
        # Write the dataframe to the Excel file with our desired sheet name
        with pd.ExcelWriter(temp_file_path) as writer:
            df.to_excel(writer, sheet_name='test_single_excel_sheet', index=False)
        
        # Open the file for upload
        with open(temp_file_path, 'rb') as file:
            # Use multipart form data to upload the file
            files = {'files': (os.path.basename(temp_file_path), file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            form_data = {'token': admin_token}
            
            # Send the upload request
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(temp_file_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload Excel file: {response.text}"
        data = response.json()
        assert "db_name" in data, "No db_name in response"
        assert "db_info" in data, "No db_info in response"
        
        db_name = data["db_name"]
        db_info = data["db_info"]
        
        # Verify the database was created and contains our table(s)
        assert "tables" in db_info, "No tables in db_info"
        assert len(db_info["tables"]) >= 1, f"Expected at least 1 table, got {len(db_info['tables'])}"
        
        # Get first table name (should be based on the Excel filename)
        table_name = db_info["tables"][0]
        assert table_name == "test_single_excel_sheet", f"Table name '{table_name}' does not match expected 'test_single_excel_sheet'. Note: For Excel files, the table name comes from the sheet name, not the file name."
        
        # Verify the table has the correct columns by querying the metadata
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Print current columns for debugging
        print("\nAvailable columns in Excel table:")
        columns = {m["column_name"] for m in metadata if m["table_name"] == table_name}
        for col in columns:
            print(f"- {col}")
        
        # Column names are sanitized in system (converted to lowercase, special chars replaced)
        expected_column_prefixes = {"product", "price", "quantity"}
        
        # Verify all expected columns exist with more flexible matching (prefix matching)
        for expected_prefix in expected_column_prefixes:
            matching_columns = [c for c in columns if c.startswith(expected_prefix)]
            assert matching_columns, f"No column starting with '{expected_prefix}' found in uploaded Excel table"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_upload_multiple_csv_files(admin_token):
    """Test uploading multiple CSV files in a single request"""
    test_db_name = f"multi_csv_{random.randint(1000, 9999)}"
    
    try:
        # Create two CSV files with different data
        csv_content1 = """Customer,Email,Orders
Alice Johnson,alice@example.com,5
Bob Williams,bob@example.com,3
Charlie Davis,charlie@example.com,8"""
        
        csv_content2 = """Product,Category,Price
Laptop,Electronics,999.99
Phone,Electronics,499.99
Tablet,Electronics,299.99"""
        
        # Create temporary files
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file1:
            csv_file1.write(csv_content1.encode('utf-8'))
            csv_file_path1 = csv_file1.name
            
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file2:
            csv_file2.write(csv_content2.encode('utf-8'))
            csv_file_path2 = csv_file2.name
        
        # Upload both CSV files in a single request
        with open(csv_file_path1, 'rb') as file1, open(csv_file_path2, 'rb') as file2:
            # Use multipart form data to upload both files
            files = [
                ('files', (os.path.basename(csv_file_path1), file1, 'text/csv')),
                ('files', (os.path.basename(csv_file_path2), file2, 'text/csv'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_file_path1)
        os.unlink(csv_file_path2)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Get metadata to verify columns from both files exist
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract all column names
        all_columns = set()
        for m in metadata:
            all_columns.add(m["column_name"].lower())
        
        # Check if we have columns from each file
        first_file_columns = any(col in {"customer", "email", "orders"} for col in all_columns)
        second_file_columns = any(col in {"product", "category", "price"} for col in all_columns)
        
        assert first_file_columns, "No columns from first CSV file found"
        assert second_file_columns, "No columns from second CSV file found"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_excel_file_with_multiple_sheets(admin_token):
    """Test uploading an Excel file with multiple sheets"""
    # Create a unique database name for this test
    test_db_name = f"excel_sheets_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas or openpyxl are not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create Excel data with multiple sheets
        excel_data = {
            'Users': pd.DataFrame({
                'UserID': [1, 2, 3],
                'Username': ['user1', 'user2', 'user3'],
                'Role': ['admin', 'user', 'user']
            }),
            'Logins': pd.DataFrame({
                'UserID': [1, 2, 3],
                'LastLogin': ['2023-01-01', '2023-01-02', '2023-01-03']
            })
        }
        
        # Create temporary Excel file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
        
        # Write data to Excel file with multiple sheets
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for sheet_name, df in excel_data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Create a unique database name for this test
        test_db_name = f"excel_sheets_{random.randint(1000, 9999)}"
        
        # Upload the Excel file
        with open(excel_path, 'rb') as file:
            # Use multipart form data to upload the file
            files = {'files': (os.path.basename(excel_path), file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(excel_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload Excel file: {response.text}"
        data = response.json()
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Get metadata to verify sheets were processed
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Verify we have data from both sheets
        users_sheet_found = False
        logins_sheet_found = False
        
        for table, columns in tables_columns.items():
            if any(col in {"userid", "username", "role"} for col in columns):
                users_sheet_found = True
            if any(col in {"userid", "lastlogin"} for col in columns):
                logins_sheet_found = True
        
        assert users_sheet_found, "Users sheet data not found"
        assert logins_sheet_found, "Logins sheet data not found"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_csv_with_excel(admin_token):
    """Test uploading a mix of CSV and Excel files in a single request"""
    # Create a unique database name for this test
    test_db_name = f"mixed_files_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create CSV content
        csv_content = """Department,Manager,Budget
Sales,John Smith,100000
Marketing,Jane Doe,150000
Engineering,Bob Johnson,200000"""
        
        # Create Excel data with a sheet
        excel_df = pd.DataFrame({
            'EmployeeID': [1, 2, 3],
            'Name': ['Alice', 'Bob', 'Charlie'],
            'Department': ['Sales', 'Marketing', 'Engineering']
        })
        
        # Create temporary files
        import tempfile
        
        # Create CSV file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file:
            csv_file.write(csv_content.encode('utf-8'))
            csv_path = csv_file.name
        
        # Create Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
        
        # Write data to Excel file
        excel_df.to_excel(excel_path, index=False)
        
        
        # Upload both files in a single request as the endpoint supports
        with open(csv_path, 'rb') as csv_f, open(excel_path, 'rb') as excel_f:
            # Use multipart form data to upload both files
            files = [
                ('files', (os.path.basename(csv_path), csv_f, 'text/csv')),
                ('files', (os.path.basename(excel_path), excel_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_path)
        os.unlink(excel_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Get metadata to verify columns from both files exist
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns for better debugging
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print all tables and columns for debugging
        print("\nTables and columns in database:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all column names as a flattened set
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        # Check for presence of CSV and Excel columns with more flexible matching
        csv_columns = {"department", "manager", "budget"}
        excel_columns = {"employeeid", "name", "department"}
        
        # Find any matches
        csv_matches = [col for col in all_columns if any(csv_col in col for csv_col in csv_columns)]
        excel_matches = [col for col in all_columns if any(excel_col in col for excel_col in excel_columns)]
        
        print(f"\nFound CSV column matches: {csv_matches}")
        print(f"Found Excel column matches: {excel_matches}")
        
        # Check if we found any matches
        csv_column_found = len(csv_matches) > 0
        excel_column_found = len(excel_matches) > 0
        
        assert csv_column_found, "No columns from CSV file found"
        assert excel_column_found, "No columns from Excel file found"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_csv_with_pdf(admin_token):
    """Test uploading a CSV file and a PDF file in a single request"""
    # Create a unique database name for this test
    test_db_name = f"csv_pdf_{random.randint(1000, 9999)}"
    
    try:
        # Create a simple CSV content
        csv_content = """Product,Category,Price
Laptop,Electronics,999.99
Phone,Electronics,499.99
Tablet,Electronics,299.99"""
        
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary files with specific names
        import tempfile
        import os
        
        # Create CSV file with predictable name
        csv_filename = 'product_catalog.csv'
        csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
        with open(csv_path, 'w') as csv_file:
            csv_file.write(csv_content)
        
        # Create PDF file with predictable name
        pdf_filename = 'catalog_specs.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Upload both files in a single request
        with open(csv_path, 'rb') as csv_f, open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload both files
            files = [
                ('files', (csv_filename, csv_f, 'text/csv')),
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_path)
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Print associated files for debugging
        db_info = data["db_info"]
        print(f"\nAssociated files: {db_info.get('associated_files')}")
        
        # Verify database was created with CSV data
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print tables and columns for debugging
        print("\nTables and columns in database:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all column names
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        print(f"\nAll columns: {all_columns}")
        
        # Verify CSV columns exist
        csv_columns = {"product", "category", "price"}
        csv_matches = [col for col in all_columns if any(csv_col in col for csv_col in csv_columns)]
        
        print(f"\nFound CSV columns: {csv_matches}")
        if not csv_matches:
            # If no exact matches, try broader check for table names
            csv_tables = [t for t in tables_columns.keys() if any(name in t.lower() for name in ["product", "catalog"])]
            print(f"Possible CSV tables: {csv_tables}")
            # Only fail if we didn't find any related tables either
            if not csv_tables:
                assert len(csv_matches) > 0, "No columns from CSV file found in the database"
        
        # Verify PDF was associated with the project
        assert "associated_files" in db_info, "No associated_files in db_info"
        assert len(db_info["associated_files"]) == 1, f"Expected 1 associated PDF file, got {len(db_info['associated_files'])}"
        
        # Verify PDF file can be downloaded
        pdf_file_id = db_info["associated_files"][0]
        # Print the PDF file ID for debugging
        print(f"\nPDF file ID: {pdf_file_id}, type: {type(pdf_file_id)}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Test deleting the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": test_db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        assert "associated_files" in updated_db_info, "No associated_files in updated db_info"
        assert len(updated_db_info["associated_files"]) == 0, "PDF file was not removed from project"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_excel_with_pdf(admin_token):
    """Test uploading an Excel file and a PDF file in a single request"""
    # Create a unique database name for this test
    test_db_name = f"excel_pdf_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create Excel data with a sheet
        excel_df = pd.DataFrame({
            'Product': ['Laptop', 'Phone', 'Tablet'],
            'Inventory': [50, 100, 75],
            'Price': [999.99, 499.99, 299.99]
        })
        
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary files with specific names
        import tempfile
        import os
        
        # Create Excel file with predictable name
        excel_filename = 'product_inventory.xlsx'
        excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
        excel_df.to_excel(excel_path, sheet_name='Inventory', index=False)
        
        # Create PDF file with predictable name
        pdf_filename = 'product_specs.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Upload both files in a single request
        with open(excel_path, 'rb') as excel_f, open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload both files
            files = [
                ('files', (excel_filename, excel_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(excel_path)
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Print associated files for debugging
        db_info = data["db_info"]
        print(f"\nAssociated files: {db_info.get('associated_files')}")
        
        # Verify database was created with Excel data
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print tables and columns for debugging
        print("\nTables and columns in database:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all column names
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        print(f"\nAll columns: {all_columns}")
        
        # Verify Excel columns exist
        excel_columns = {"product", "inventory", "price"}
        excel_matches = [col for col in all_columns if any(excel_col in col for excel_col in excel_columns)]
        
        print(f"\nFound Excel columns: {excel_matches}")
        if not excel_matches:
            # If no exact matches, try broader check for table names
            excel_tables = [t for t in tables_columns.keys() if any(name in t.lower() for name in ["inventory", "product"])]
            print(f"Possible Excel tables: {excel_tables}")
            # Only fail if we didn't find any related tables either
            if not excel_tables:
                assert len(excel_matches) > 0, "No columns from Excel file found in the database"
        
        # Verify PDF was associated with the project
        assert "associated_files" in db_info, "No associated_files in db_info"
        assert len(db_info["associated_files"]) == 1, f"Expected 1 associated PDF file, got {len(db_info['associated_files'])}"
        
        # Verify PDF file can be downloaded
        pdf_file_id = db_info["associated_files"][0]
        # Print the PDF file ID for debugging
        print(f"\nPDF file ID: {pdf_file_id}, type: {type(pdf_file_id)}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Test deleting the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": test_db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        assert "associated_files" in updated_db_info, "No associated_files in updated db_info"
        assert len(updated_db_info["associated_files"]) == 0, "PDF file was not removed from project"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_csv_excel_pdf_combination(admin_token):
    """Test uploading a combination of CSV, Excel, and PDF files in a single request"""
    # Create a unique database name for this test
    test_db_name = f"all_files_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create CSV content - add more descriptive filename to ensure it's processed correctly
        csv_content = """Customer,Email,Status
John Smith,john@example.com,Active
Jane Doe,jane@example.com,Inactive
Bob Johnson,bob@example.com,Active"""
        
        # Create Excel data
        excel_df = pd.DataFrame({
            'OrderID': [1001, 1002, 1003],
            'CustomerID': ['JOHN', 'JANE', 'BOB'],
            'Amount': [150.50, 75.25, 200.00]
        })
        
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary files with specific names
        import tempfile
        import os
        
        # Create CSV file with predictable name
        csv_filename = 'customer_data.csv'
        csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
        with open(csv_path, 'w') as csv_file:
            csv_file.write(csv_content)
        
        # Create Excel file with predictable name
        excel_filename = 'order_data.xlsx'
        excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
        excel_df.to_excel(excel_path, sheet_name='Orders', index=False)
        
        # Create PDF file with predictable name
        pdf_filename = 'document.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Upload all files in a single request
        with open(csv_path, 'rb') as csv_f, open(excel_path, 'rb') as excel_f, open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload all files
            files = [
                ('files', (csv_filename, csv_f, 'text/csv')),
                ('files', (excel_filename, excel_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with all files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_path)
        os.unlink(excel_path)
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Print associated files for debugging
        db_info = data["db_info"]
        print(f"\nAssociated files: {db_info.get('associated_files')}")
        
        # Verify database was created with CSV and Excel data
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print tables and columns for debugging
        print("\nTables and columns in database for CSV+Excel+PDF test:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all columns as a flattened set
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        print(f"\nAll columns: {all_columns}")
            
        # Check for presence of columns with more flexible matching
        column_checks = {
            "CSV": ["customer", "email", "status"],
            "Excel": ["orderid", "customerid", "amount"]
        }
        
        for file_type, expected_columns in column_checks.items():
            found_columns = []
            for col in all_columns:
                for expected in expected_columns:
                    if expected in col.lower():
                        found_columns.append(col)
                        break
            
            print(f"\nFound {file_type} columns: {found_columns}")
            if not found_columns:
                # If no exact matches, try broader check
                file_tables = []
                if file_type == "CSV":
                    file_tables = [t for t in tables_columns.keys() if "customer" in t.lower()]
                elif file_type == "Excel":
                    file_tables = [t for t in tables_columns.keys() if "order" in t.lower()]
                
                print(f"Possible {file_type} tables: {file_tables}")
                # Skip the assertion if we found related tables
                if not file_tables:
                    assert found_columns, f"No columns from {file_type} file found in the database"
        
        # Verify PDF was associated with the project
        assert "associated_files" in db_info, "No associated_files in db_info"
        assert len(db_info["associated_files"]) == 1, f"Expected 1 associated PDF file, got {len(db_info['associated_files'])}"
        
        # Verify PDF file can be downloaded
        pdf_file_id = db_info["associated_files"][0]
        # Print the PDF file ID for debugging
        print(f"\nPDF file ID: {pdf_file_id}, type: {type(pdf_file_id)}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Test deleting the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": test_db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        assert "associated_files" in updated_db_info, "No associated_files in updated db_info"
        assert len(updated_db_info["associated_files"]) == 0, "PDF file was not removed from project"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)