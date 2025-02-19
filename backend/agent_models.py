from typing import Any, Optional
from pydantic import BaseModel


class Inputs(BaseModel):
    question: str
    hard_filters: list
    db_name: str
    previous_context: list


class Clarification(BaseModel):
    question: str
    answer: str


class PreviousContextItem(BaseModel):
    question: str
    sql: str


class AnalysisData(BaseModel):
    analysis_id: str
    db_name: str
    initial_question: Optional[str] = None
    tool_name: Optional[str] = None
    last_inputs: Optional[Inputs] = None
    inputs: Optional[Inputs] = None
    clarification_questions: Optional[list[Clarification]] = None
    assignment_understanding: Optional[str] = None
    previous_context: Optional[list[PreviousContextItem]] = None
    input_metadata: Optional[dict[str, dict]] = None
    sql: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
