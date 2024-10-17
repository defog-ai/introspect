import asyncio
import json
from io import StringIO
import os
from typing import Any, Dict

import pandas as pd

from utils_logging import LOGGER
from generic_utils import make_request

# import random
# import time
# import traceback
# from db_utils import get_db_type_creds

# from oracle.utils_explore_data import (
#     TABLE_CSV,
#     IMAGE,
#     gen_sql,
#     get_chart_fn,
#     gen_data_analysis,
#     retry_sql_gen,
#     run_chart_fn,
# )
# from utils_sql import execute_sql

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


async def optimize(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function is run after the explore stage, and if the task_type
    was "optimization".

    This function will optimize the objective input by the user, considering
    the context, data, and predictions generated.

    This figures out what kind of optimizations the user requested for, and how we can do those optimization.

    These are the subtask options it will consider:
    1. `simple_recommendation`:
        - This simply feeds the outputs from explore to an LLM and generates a simple text based recommendations
          after looking at the data.
        - Ideally, this should be able to run simple anlaysis on the outputs, if it needs any specific details like
          average, max, min etc.
    2. `run_optimizer_model`:
        - This runs a mathematical optimizer function.
        - The LLM will figure out the constraints and objectives, and this function will run an optimizer based on those.
        - We will formulate the optimization problem as a linear program, solve it using a solver, and return the optimal
          solution(s) or infeasibility if found.

    It will create a task array, where each task has a subtask type from above, and the required inputs for running that task:
    ```
    {
      task_type: "simple_recommendation" or "run_optimizer_model",
      "inputs": Inputs required for the optimizer. No inputs are required for "simple_recommendation".
    }
    ```

    It will run the above tasks in parallel, and return the resulting outputs of each of them.
    """
    LOGGER.info(f"[Optimize] Optimizing for report {report_id}")
    LOGGER.debug(f"[Optimize] Inputs: {inputs}")
    LOGGER.debug(f"[Optimize] Outputs: {outputs}")

    user_question = inputs["user_question"]

    # look at the user question, and make a decision on
    # whether we want to do simple_recommendation or run_optimizer_model
    resp = await make_request(
        DEFOG_BASE_URL + "/oracle/gen_optimization_tasks",
        data={
            "question": user_question,
            "api_key": api_key,
            "username": username,
            "report_id": report_id,
            "task_type": task_type,
            "gather_context": outputs.get("gather_context", {}),
            "explore": outputs.get("explore", {}),
        },
    )
    task = resp.get("task", [])

    LOGGER.info(f"Optimizer task: {json.dumps(task, indent=2)}")
    return {"optimization": "optimization completed"}
