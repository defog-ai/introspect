from enum import Enum
import os

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
INTERNAL_DB = os.environ.get("INTERNAL_DB", "postgres")


class TaskType(Enum):
    EXPLORATION = "exploration"

    def __json__(self):
        return self.value


TASK_TYPES = [
    TaskType.EXPLORATION,
]


class TaskStage(Enum):
    GATHER_CONTEXT = "gather_context"
    EXPLORE = "explore"
    EXPORT = "export"
    DONE = "done"


STAGE_TO_STATUS = {
    TaskStage.GATHER_CONTEXT: "gathering context",
    TaskStage.EXPLORE: "exploring data and digging deeper",
    TaskStage.EXPORT: "finalizing and exporting",
    TaskStage.DONE: "done",
}
