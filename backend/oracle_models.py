from enum import Enum
from typing import List, Dict, Any, Optional
import logging

from pydantic import BaseModel
from llm_api import GPT_4O_MINI
from utils_logging import LOG_LEVEL

LOGGER = logging.getLogger("oracle")
LOGGER.setLevel(LOG_LEVEL)


class TASK_TYPE(Enum):
    EXPLORATION = "exploration"
    PREDICTION = "prediction"
    OPTIMIZATION = "optimization"


# all task type string values:
TASK_TYPES = [task_type.value for task_type in TASK_TYPE]


# stages
GATHER_CONTEXT = "gather_context"
WAIT_CLARIFICATIONS = "wait_clarifications"
EXPLORE = "explore"
PREDICT = "predict"
OPTIMIZE = "optimize"
EXPORT = "export"


OPEN_AI_MODEL = GPT_4O_MINI


class InputType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    NUMBER = "number"
    TEXT = "text"


class Clarification(BaseModel):
    clarification: str
    input_type: Optional[InputType] = None
    options: Optional[list[str]] = None
    answer: Optional[str] = None


class Inputs(BaseModel):
    """
    These are the explicit user inputs to the oracle.
    """

    user_question: str
    sources: List[Dict[str, Any]]
    clarifications: List[Clarification]


class GatherContext(BaseModel):
    problem_statement: str
    context: str
    sources: List[Dict[str, Any]]
    issues: List[str]


class ExploreArtifact(BaseModel):
    artifact_content: str = ""
    artifact_description: str = ""
    artifact_location: str = ""


class ExploreWorking(BaseModel):
    generated_sql: str


class ExploreAnalysis(BaseModel):
    qn_id: int
    generated_qn: str
    artifacts: Dict[str, ExploreArtifact]
    working: ExploreWorking
    title: str = ""
    summary: str = ""


class KeyMetric(BaseModel):
    description: str
    table_column: List[str]


class Explore(BaseModel):
    analyses: List[ExploreAnalysis]
    key_metric: KeyMetric
    summary: str


class PredictWorking(BaseModel):
    target: str
    features: str
    unit_of_analysis: str
    prediction_sql: str


class Predict(BaseModel):
    model_path: str
    chart_paths: List[str]
    working: PredictWorking
    prediction_summary: str


class Optimize(BaseModel):
    recommendations: List[str]


class Outputs(BaseModel):
    gather_context: GatherContext
    explore: Explore
    predict: Optional[Predict] = None
    optimize: Optional[Optimize] = None


class GenerateReportRequest(BaseModel):
    """
    This is the request for generating a report.
    Use generate_report_guidelines for the following:
    - specifying the audience of the report
    - specifying the format / structure / tone / length of the report
    - specifying any types of actions / recommendations that the report should
      include or exclude (e.g. "exclude actions that are not actionable")
    """

    api_key: str
    task_type: TASK_TYPE
    inputs: Inputs
    outputs: Outputs
    generate_report_guidelines: str = ""


class Recommendation(BaseModel):
    title: str
    insight: str
    action: str
    analysis_reference: List[int]


class ReportSummary(BaseModel):
    title: str
    introduction: str
    recommendations: List[Recommendation]


class GenerateReportSummaryResponse(BaseModel):
    summary_dict: ReportSummary
