from pydantic import BaseModel, Field
from typing import List, Any

class AnswerQuestionFromDatabaseInput(BaseModel):
    question: str = Field(..., description="The question to generate SQL for")
    db_name: str = Field(..., description="The name of database to generate SQL for. "
    "This will help the function identify the DDL statements and instruction manual "
    "associated with this database.")

class AnswerQuestionFromDatabaseOutput(BaseModel):
    sql: str = Field(..., description="The SQL query generated from the question")
    colnames: List[str] = Field(..., description="The column names of the table (header row)")
    rows: List[List[Any]] = Field(..., description="The rows of the table generated from SQL (data rows)")

