"""Tests for user management functionality."""

import requests
import sys
import os

from .conftest import BASE_URL


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