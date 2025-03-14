"""Authentication tests for the Defog backend API."""

from .conftest import BASE_URL

def test_admin_login(admin_token):
    """Test admin login functionality i.e. the token returned is not None"""
    assert admin_token is not None