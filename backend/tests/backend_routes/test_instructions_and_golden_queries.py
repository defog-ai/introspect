"""Tests for content management features including instructions and golden queries."""

import requests
import sys
import os

from .conftest import BASE_URL, TEST_DB


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