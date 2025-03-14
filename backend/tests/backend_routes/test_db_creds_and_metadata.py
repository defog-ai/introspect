"""Tests for database management and metadata functionality."""

import json
import requests
import sys
import os

# Get the conftest directly from the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from conftest import BASE_URL, TEST_DB, cleanup_test_database


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