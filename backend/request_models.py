from typing import Any, Literal
from pydantic import BaseModel


class UserRequest(BaseModel):
    """
    Request model for user requests.
    `token` is used for authentication.
    `db_name` defines a given user profile, which is a set of metadata, glossary,
    golden queries, database credentials, etc.
    """

    token: str
    db_name: str


class LoginRequest(BaseModel):
    username: str
    password: str


class MetadataGetRequest(UserRequest):
    """
    Request model for metadata get requests.
    format can be either csv or json or None
    """

    format: Literal["csv", "json", None] = None


class ColumnMetadata(BaseModel):
    table_name: str
    column_name: str
    data_type: str
    column_description: str


class MetadataUpdateRequest(UserRequest):
    """
    Request model for updating metadata.
    metadata is a list of ColumnMetadata objects.
    """

    metadata: list[ColumnMetadata]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "my_token",
                    "db_name": "my_key_name",
                    "metadata": [
                        {
                            "table_name": "users_table",
                            "column_name": "username",
                            "data_type": "text",
                            "column_description": "username of the user",
                        }
                    ],
                }
            ]
        }
    }


class MetadataGenerateRequest(UserRequest):
    """
    Request model for generating metadata.
    """

    tables: Any = []

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "my_token",
                    "db_name": "my_key_name",
                    "tables": ["users_table", "orders_table"],
                }
            ]
        }
    }


class InstructionsUpdateRequest(UserRequest):
    """
    Request model for updating instructions.
    """

    instructions: str


class GoldenQuery(BaseModel):
    question: str
    sql: str


class GoldenQueriesUpdateRequest(UserRequest):
    """
    Request model for updating golden queries.
    """

    golden_queries: list[GoldenQuery]


class GoldenQueriesDeleteRequest(UserRequest):
    """
    Request model for deleting golden queries.
    """

    questions: list[str]
