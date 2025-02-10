from typing import Literal
from pydantic import BaseModel

class UserRequest(BaseModel):
    """
    Request model for user requests.
    `token` is used for authentication.
    `key_name` defines a given user profile, which is a set of metadata, glossary,
    golden queries, database credentials, etc.
    """
    token: str
    key_name: str

class LoginRequest(BaseModel):
    username: str
    password: str

class MetadataGetRequest(UserRequest):
    """
    Request model for metadata get requests.
    format can be either csv or json or None
    """
    format: Literal["csv", "json", None] = None
