"""Tests for Oracle report generation functionality."""

import requests
import pytest

from .conftest import BASE_URL, TEST_DB


def test_oracle_report_generation(admin_token):
    """Test the oracle report generation flow including clarifications and report generation"""
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
        
        # Create minimal metadata for test
        metadata = [
            {
                "table_name": "customers",
                "column_name": "id",
                "data_type": "integer",
                "column_description": "Unique identifier for customers",
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
        
        # Update metadata to ensure it exists
        metadata_response = requests.post(
            f"{BASE_URL}/integration/update_metadata",
            json={"token": admin_token, "db_name": db_name, "metadata": metadata},
        )
        assert metadata_response.status_code == 200, f"Failed to update metadata: {metadata_response.text}"

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
                "clarifications": answered_clarifications,
                "use_multi_agent": False
            },
            headers={"Content-Type": "application/json"},
        )

        # Check report response
        assert report_response.status_code == 200, f"Failed to generate report: {report_response.text}"
        report_data = report_response.json()

        # Verify report content
        assert "mdx" in report_data, "No MDX content in report response"
        assert "sql_answers" in report_data, "No sql_answers in report response"
        
        # Ensure no error in response and validate content quality
        assert "error" not in report_data or not report_data["error"], f"Error in report response: {report_data.get('error')}"
        assert len(report_data["mdx"]) > 100, "Report content too short to be valid"
        
        # Validate SQL answers
        if report_data["sql_answers"]:
            for sql_answer in report_data["sql_answers"]:
                assert "error" not in sql_answer or not sql_answer["error"], f"Error in SQL answer: {sql_answer.get('error')}"
                assert "sql" in sql_answer and sql_answer["sql"], "SQL query missing or empty in SQL answer"

        print("\nGenerated Report:")
        print(report_data["mdx"])

    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


# @pytest.mark.skip(reason="Multi-agent test takes longer to run, use only when needed")
def test_multi_agent_report_generation(admin_token):
    """Test the multi-agent oracle report generation which uses specialized agent phases"""
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
        
        # Create minimal metadata for test
        metadata = [
            {
                "table_name": "customers",
                "column_name": "id",
                "data_type": "integer",
                "column_description": "Unique identifier for customers",
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
        
        # Update metadata to ensure it exists
        metadata_response = requests.post(
            f"{BASE_URL}/integration/update_metadata",
            json={"token": admin_token, "db_name": db_name, "metadata": metadata},
        )
        assert metadata_response.status_code == 200, f"Failed to update metadata: {metadata_response.text}"

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

        print("\nReceived clarification questions for multi-agent report:")
        for c in clarifications:
            print(f"- {c['clarification']}")
            if 'options' in c:
                print(f"  Options: {c['options']}")

        # Answer a couple expected clarifications
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

        # Generate the report using multi-agent approach
        report_response = requests.post(
            f"{BASE_URL}/oracle/generate_report",
            json={
                "report_id": report_id,
                "token": admin_token,
                "db_name": db_name,
                "user_question": user_question,
                "clarifications": answered_clarifications,
                "use_multi_agent": True
            },
            headers={"Content-Type": "application/json"},
        )

        # Check report response
        assert report_response.status_code == 200, f"Failed to generate report with multi-agent approach: {report_response.text}"
        report_data = report_response.json()

        # Verify report content
        assert "mdx" in report_data, "No MDX content in report response"
        assert "sql_answers" in report_data, "No sql_answers in report response"
        
        # Ensure no error in response and validate content quality
        assert "error" not in report_data or not report_data["error"], f"Error in report response: {report_data.get('error')}"
        assert len(report_data["mdx"]) > 100, "Report content too short to be valid"
        
        # Validate SQL answers
        if report_data["sql_answers"]:
            for sql_answer in report_data["sql_answers"]:
                assert "error" not in sql_answer or not sql_answer["error"], f"Error in SQL answer: {sql_answer.get('error')}"
                assert "sql" in sql_answer and sql_answer["sql"], "SQL query missing or empty in SQL answer"

        print("\nGenerated Multi-Agent Report:")
        print(report_data["mdx"])

    except Exception as e:
        print(f"\nMulti-agent test failed with error: {str(e)}")
        raise e