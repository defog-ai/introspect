from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict


class UserRequest(BaseModel):
    """
    Request model for user requests.
    `token` is used for authentication.
    `db_name` defines a given user profile, which is a set of metadata, glossary,
    golden queries, database credentials, etc.
    """

    token: str
    db_name: Optional[str] = None


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


class TableDescription(BaseModel):
    table_name: str
    table_description: str

class TableDescriptionsUpdateRequest(UserRequest):
    """
    Request model for updating table descriptions.
    """

    table_descriptions: list[TableDescription]


class InstructionsUpdateRequest(UserRequest):
    """
    Request model for updating instructions.
    """

    instructions: str


class JoinHintsUpdateRequest(UserRequest):
    """
    Request model for updating join hints.
    Will delete the existing join hints if join_hints is None.
    """

    join_hints: list[list[str]] | None = None


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


class HardFilter(BaseModel):
    table_name: str
    column_name: str
    operator: str
    value: str


class QuestionAnswer(BaseModel):
    question: str
    answer: str


class GenerateSQLQueryRequest(UserRequest):
    """
    Request model for generating SQL queries.
    """

    question: str
    db_type: str | None = None
    metadata: list[ColumnMetadata] = []
    table_descriptions: list[TableDescription] = []
    instructions: str = ""
    previous_context: list[QuestionAnswer] = []
    hard_filters: list[HardFilter] = []

    # optional prompt-level parameters
    num_golden_queries: int = 4
    model_name: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "123",
                    "db_name": "my_key_name",
                    "question": "Show me any 5 rows from the first table",
                },
                {
                    "token": "123",
                    "db_name": "my_key_name",
                    "question": "Show me any 5 rows from the first table",
                    "instructions": "",
                    "metadata": [
                        {
                            "table_name": "table1",
                            "column_name": "column1",
                            "data_type": "int",
                            "column_description": "",
                        },
                        {
                            "table_name": "table1",
                            "column_name": "column2",
                            "data_type": "varchar",
                            "column_description": "",
                        },
                    ],
                    "previous_context": [],
                    "hard_filters": [
                        {
                            "table_name": "table1",
                            "column_name": "column1",
                            "operator": "=",
                            "value": "1",
                        }
                    ],
                    "num_golden_queries": 2,
                    "model_name": "gpt-4o-mini",
                },
            ]
        }
    }


UserTableRow = dict[str, Any]


class UserTableColumn(BaseModel):
    title: str

    model_config = ConfigDict(extra="allow")


class UserTable(BaseModel):
    rows: Optional[list[UserTableRow]] = None
    columns: list[UserTableColumn]


class UploadFileAsDBRequest(UserRequest):
    """
    Request model for uploading a file as a database.
    """
    file_name: str
    tables: dict[str, UserTable]


class AnswerQuestionFromDatabaseRequest(UserRequest):
    """
    Request model for answering a question from a database.
    """
    question: str
    model: str | None = None


class SynthesizeReportFromQuestionRequest(UserRequest):
    """
    Request model for synthesizing a report from a question.
    `num_reports` is the number of intermediate reports to generate and
    synthesize into a final report.
    """
    question: str
    model: str | None = None
    num_reports: int = 3


class WebSearchRequest(UserRequest):
    """
    Request model for performing a web search.
    """
    question: str
