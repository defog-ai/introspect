"""Tests for query generation and execution functionality."""

import asyncio
import requests
import sys
import os

# Get the conftest directly from the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from conftest import BASE_URL, TEST_DB
from utils_sql import execute_sql


def test_generate_query(admin_token):
    """Test SQL query generation"""
    try:
        # Use our test database configuration
        db_name = TEST_DB["db_name"]

        # First, ensure DB credentials are set up
        add_creds_payload = {
            "token": admin_token,
            "db_name": db_name,
            "db_type": TEST_DB["db_type"],
            "db_creds": TEST_DB["db_creds"],
        }
        response = requests.post(
            f"{BASE_URL}/integration/update_db_creds", json=add_creds_payload
        )
        assert response.status_code == 200, f"Failed to set up database credentials. Response: {response.text}"
        
        # Create metadata list for test data
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
            }
        ]
        
        # Update metadata to ensure it exists
        metadata_response = requests.post(
            f"{BASE_URL}/integration/update_metadata",
            json={"token": admin_token, "db_name": db_name, "metadata": metadata},
        )
        assert metadata_response.status_code == 200, f"Failed to update metadata: {metadata_response.text}"

        # Now generate a SQL query
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


