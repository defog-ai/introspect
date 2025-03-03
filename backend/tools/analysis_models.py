from pydantic import BaseModel, Field
from typing import List, Any, Optional
import uuid


class AnswerQuestionInput(BaseModel):
    question: str = Field(..., description="The question to generate SQL for")


class AnswerQuestionFromDatabaseInput(AnswerQuestionInput):
    db_name: str = Field(
        ...,
        description="The name of database to generate SQL for. "
        "This will help the function identify the DDL statements and instruction manual "
        "associated with this database.",
    )


class AnswerQuestionViaPDFCitationsInput(AnswerQuestionInput):
    pdf_files: List[int] = Field(
        ..., description="The ids of the PDFs to use for citation"
    )


class AnswerQuestionFromDatabaseOutput(BaseModel):

    analysis_id: Optional[str] = Field(
        default=None,
        description="The analysis ID. Will be later used for source citation.",
    )
    question: Optional[str] = Field(..., description="The question to generate SQL for")
    sql: Optional[str] = Field(
        default=None, description="The SQL query generated from the question"
    )
    columns: Optional[List[str]] = Field(
        default=None, description="The columns returned by the SQL query"
    )
    rows: Optional[str] = Field(
        default=None,
        description="The JSON string representation of the dataframe returned by the SQL query",
    )
    df_truncated: Optional[bool] = Field(
        default=None, description="Whether the dataframe was truncated"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")


class InspectHeadInput(BaseModel):
    table_name: str = Field(..., description="The name of the table to inspect")
    db_name: str = Field(..., description="The name of the database to inspect")


class InspectHeadOutput(BaseModel):
    columns: Optional[List[str]] = Field(
        default=None, description="The columns returned by the SQL query"
    )
    rows: Optional[str] = Field(
        default=None,
        description="The JSON string representation of the dataframe returned by the SQL query",
    )
    error: Optional[str] = Field(default=None, description="Error message if any")


class GenerateReportFromQuestionInput(BaseModel):
    report_id: str = Field(..., description="The report ID")
    question: str = Field(..., description="The initial question to generate SQL for")
    model: str = Field(
        ..., description="The name of the model to use for generating SQL. "
    )
    db_name: str = Field(..., description="The name of database to generate SQL for. ")
    clarification_responses: Optional[str] = Field(
        default="",
        description="The clarifications provided by the user after asking the initial question.",
    )
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
    tool_outputs: List[Any] = Field(
        ..., description="The tool outputs used to generate the report"
    )


class SynthesizeReportFromQuestionsOutput(BaseModel):
    synthesized_report: str = Field(
        ..., description="The final report synthesized from the questions"
    )
    report_answers: List[GenerateReportFromQuestionOutput] = Field(
        ..., description="The intermediate reports used to synthesize the final report"
    )
