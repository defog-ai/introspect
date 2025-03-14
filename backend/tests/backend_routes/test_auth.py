"""Authentication tests for the Defog backend API."""

import sys
import os

# Get the conftest directly from the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from conftest import BASE_URL

def test_admin_login(admin_token):
    """Test admin login functionality i.e. the token returned is not None"""
    assert admin_token is not None