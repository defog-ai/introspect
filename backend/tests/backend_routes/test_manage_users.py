"""Tests for user management functionality."""

import requests
import sys
import os

from .conftest import BASE_URL


def test_add_users_batch(admin_token):
    """Test adding and updating users via CSV content"""
    try:
        test_users = [
            {"email": "test.user1@example.com", "password": "TestPass1!"},
            {"email": "test.user2@example.com", "password": "TestPass2!"},
        ]
        test_users_csv = "username,password,user_type\n" + \
            "\n".join([f"{u['email']},{u['password']},GENERAL" for u in test_users])

        # Add users via CSV
        response = requests.post(
            f"{BASE_URL}/admin/add_users",
            json={"token": admin_token, "users_csv": test_users_csv},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, f"Failed to add users: {response.text}"
        assert response.json()["status"] == "success", "Response status is not success"

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


def test_add_single_user(admin_token):
    """Test adding a single user through the add_user endpoint"""
    try:
        # Create a single user
        test_user = {
            "username": "test.single@example.com",
            "password": "SecurePass123!",
            "user_type": "GENERAL"
        }
        
        response = requests.post(
            f"{BASE_URL}/admin/add_user",
            json={
                "token": admin_token,
                "user": test_user
            },
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, f"Failed to add user: {response.text}"
        assert response.json()["status"] == "success", "Response status is not success"
        
        # Verify the user was added
        get_response = requests.post(
            f"{BASE_URL}/admin/get_users",
            json={"token": admin_token},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, f"Failed to get users: {get_response.text}"
        
        users = get_response.json()["users"]
        user_emails = [user["username"] for user in users]
        assert test_user["username"] in user_emails, f"{test_user['username']} not found in users list"
        
        # Clean up
        delete_response = requests.post(
            f"{BASE_URL}/admin/delete_user",
            json={"token": admin_token, "username": test_user["username"]},
            headers={"Content-Type": "application/json"},
        )
        assert delete_response.status_code == 200, \
            f"Failed to delete user {test_user['username']}: {delete_response.text}"
    
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_update_user_status(admin_token):
    """Test updating a user's status"""
    try:
        # First create a test user
        test_user = {
            "username": "test.status@example.com",
            "password": "SecurePass123!",
            "user_type": "GENERAL"
        }
        
        # Add the user
        add_response = requests.post(
            f"{BASE_URL}/admin/add_user",
            json={
                "token": admin_token,
                "user": test_user
            },
            headers={"Content-Type": "application/json"},
        )
        assert add_response.status_code == 200, f"Failed to add user: {add_response.text}"
        
        # Update user status to INACTIVE
        status_response = requests.post(
            f"{BASE_URL}/admin/update_user_status",
            json={
                "token": admin_token,
                "username": test_user["username"],
                "status": "INACTIVE"
            },
            headers={"Content-Type": "application/json"},
        )
        assert status_response.status_code == 200, f"Failed to update status: {status_response.text}"
        assert status_response.json()["status"] == "success", "Status update response is not success"
        
        # Verify the status was updated
        get_response = requests.post(
            f"{BASE_URL}/admin/get_users",
            json={"token": admin_token},
            headers={"Content-Type": "application/json"},
        )
        assert get_response.status_code == 200, f"Failed to get users: {get_response.text}"
        
        users = get_response.json()["users"]
        target_user = next((user for user in users if user["username"] == test_user["username"]), None)
        assert target_user is not None, f"User {test_user['username']} not found in users list"
        assert target_user["status"] == "INACTIVE", f"User status was not updated to INACTIVE"
        
        # Clean up
        delete_response = requests.post(
            f"{BASE_URL}/admin/delete_user",
            json={"token": admin_token, "username": test_user["username"]},
            headers={"Content-Type": "application/json"},
        )
        assert delete_response.status_code == 200, \
            f"Failed to delete user {test_user['username']}: {delete_response.text}"
    
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_reset_password(admin_token):
    """Test resetting a user's password"""
    try:
        # First create a test user
        test_user = {
            "username": "test.reset@example.com", 
            "password": "OldSecurePass123!"
        }
        
        # Add the user
        add_response = requests.post(
            f"{BASE_URL}/admin/add_user",
            json={
                "token": admin_token,
                "user": test_user
            },
            headers={"Content-Type": "application/json"},
        )
        assert add_response.status_code == 200, f"Failed to add user: {add_response.text}"
        
        # Reset the user's password
        new_password = "NewSecurePass456!"
        reset_response = requests.post(
            f"{BASE_URL}/admin/reset_password",
            json={
                "token": admin_token,
                "username": test_user["username"],
                "password": new_password
            },
            headers={"Content-Type": "application/json"},
        )
        assert reset_response.status_code == 200, f"Failed to reset password: {reset_response.text}"
        
        # Verify we can login with new password
        login_response = requests.post(
            f"{BASE_URL}/login",
            json={"username": test_user["username"], "password": new_password},
        )
        assert login_response.status_code == 200, "Failed to login with new password"
        
        # Clean up
        delete_response = requests.post(
            f"{BASE_URL}/admin/delete_user",
            json={"token": admin_token, "username": test_user["username"]},
            headers={"Content-Type": "application/json"},
        )
        assert delete_response.status_code == 200, \
            f"Failed to delete user {test_user['username']}: {delete_response.text}"
    
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_update_users(admin_token):
    """Test updating an existing user's password via CSV"""
    try:
        # First create a test user
        test_user = {"email": "test.update@example.com", "password": "InitialPass123!"}
        initial_csv = f"username,password,user_type\n{test_user['email']},{test_user['password']},GENERAL"

        response = requests.post(
            f"{BASE_URL}/admin/add_users",
            json={"token": admin_token, "users_csv": initial_csv},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, "Failed to create initial user"

        # Update the user's password
        new_password = "UpdatedPass456!"
        update_csv = f"username,password,user_type\n{test_user['email']},{new_password},GENERAL"

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