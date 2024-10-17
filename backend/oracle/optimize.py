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
    # TODO implement this function
    # Once the
    # dummy print statement for now
    LOGGER.info(f"Optimizing for report {report_id}")
    LOGGER.debug(f"Optimiser inputs: {inputs}")
    LOGGER.debug(f"Optimiser outputs: {outputs}")

    user_question = inputs["user_question"]
    gather_context_results = outputs.get("gather_context", {})
    objective = gather_context_results.get("objective", "")
    constraints = gather_context_results.get("constraints", [])
    context = gather_context_results.get("context", "")

    gather_context_prompt_text = ""
    # Only keep objective, context and constraints
    # The problem_statement inside gather_context doesn't seem to add too much new info
    # Most of that information can be gleaned from the user_question itself
    if objective:
        gather_context_prompt_text += f"{objective}\n"

    if context:
        gather_context_prompt_text += f"Context: {context}\n"

    if constraints and len(constraints) > 0:
        gather_context_prompt_text += "Constraints:\n"
        for i, c in enumerate(constraints):
            gather_context_prompt_text += f"{i + 1}: {c}\n"

    gather_context_prompt_text = gather_context_prompt_text.strip()

    # now get explorer results
    # and merge them into a text snippet
    explore_results = outputs.get("explore", [])
    explore_results_prompt_text = ""

    count = 1

    for analysis in explore_results:
        title = analysis.get("title", "")
        summary = analysis.get("summary", "")
        artifacts = analysis.get("artifacts")
        table_csv = artifacts.get("table_csv", {})
        table_csv_str = table_csv.get("artifact_content", None)
        table_csv_desc = table_csv.get("artifact_description", None)
        independent_variable = analysis.get("independent_variable", "")

        if title and summary and table_csv_str and table_csv_desc:
            # parse the table_csv_str and get the columns available
            df = pd.read_csv(StringIO(table_csv_str))
            cols = ", ".join(df.columns)

            explore_results_prompt_text += (
                f"\n{count}. {title}\n"
                + f"Summary: {summary}\n"
                + f"Data generated: {table_csv_desc}\n"
                + f"Columns: {cols}\n"
                + f"Variable name: {independent_variable['name']}"
            )
            count += 1

    LOGGER.debug(f"gather_context_prompt_text: {gather_context_prompt_text}")
    LOGGER.debug(f"explore_results_prompt_text: {explore_results_prompt_text}")
    # look at the user question, and make a decision on
    # whether we want to do simple_recommendation or run_optimizer_model
    resp = await make_request(
        DEFOG_BASE_URL + "/oracle/gen_optimization_tasks",
        data={
            "question": user_question,
            "api_key": api_key,
            "gather_context_results": gather_context_prompt_text,
            "explore_results": explore_results_prompt_text,
            "username": username,
            "report_id": report_id,
            "task_type": task_type,
        },
    )
    task = resp.get("task", [])

    LOGGER.info(f"Optimizer task: {json.dumps(task, indent=2)}")
    # simple_recommendation: Just do a simple text based summary/recommendations based on the data that has been generated so far
    # run_optimizer_model: Run an optimizer function
    return {"optimization": "optimization completed"}
