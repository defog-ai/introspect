from enum import Enum
from typing import List, Dict, Any, Optional
import logging

from pydantic import BaseModel
from utils_logging import LOG_LEVEL

LOGGER = logging.getLogger("oracle")
LOGGER.setLevel(LOG_LEVEL)


class TASK_TYPE(Enum):
    EXPLORATION = "exploration"


# all task type string values:
TASK_TYPES = [task_type.value for task_type in TASK_TYPE]


# stages
GATHER_CONTEXT = "gather_context"
WAIT_CLARIFICATIONS = "wait_clarifications"
EXPLORE = "explore"


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
