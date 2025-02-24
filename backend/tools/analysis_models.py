from pydantic import BaseModel, Field
from typing import List, Any


class AnswerQuestionFromDatabaseInput(BaseModel):
    question: str = Field(..., description="The question to generate SQL for")
    db_name: str = Field(
        ...,
        description="The name of database to generate SQL for. "
        "This will help the function identify the DDL statements and instruction manual "
        "associated with this database.",
    )


class AnswerQuestionFromDatabaseOutput(BaseModel):
    sql: str = Field(..., description="The SQL query generated from the question")
    colnames: List[str] = Field(
        ..., description="The column names of the table (header row)"
    )
    rows: List[List[Any]] = Field(
        ..., description="The rows of the table generated from SQL (data rows)"
    )


class GenerateReportFromQuestionInput(BaseModel):
    question: str = Field(..., description="The initial question to generate SQL for")
    model: str = Field(
        ..., description="The name of the model to use for generating SQL. "
    )
    db_name: str = Field(..., description="The name of database to generate SQL for. ")
    num_reports: int = Field(
        default=1,
        description="The number of reports to generate. "
        "This input class is used for generating single and multiple reports."
        "The default is 1.",
    )


class GenerateReportFromQuestionOutput(BaseModel):
    report: str = Field(
        ..., description="The final report generated from the questions"
    )
    sql_answers: List[AnswerQuestionFromDatabaseOutput] = Field(
        ..., description="The SQL queries and data answers used to generate the report"
    )


class SynthesizeReportFromQuestionsOutput(BaseModel):
    report: str = Field(
        ..., description="The final report synthesized from the questions"
    )
    report_answers: List[GenerateReportFromQuestionOutput] = Field(
        ..., description="The intermediate reports used to synthesize the final report"
    )
