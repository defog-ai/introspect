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

    user_question = inputs["user_question"]
    explorer_outputs: list = outputs.get("explore", {})
    analyses = explorer_outputs.get("analyses", [])
    gather_context: dict = outputs.get("gather_context", {})

    # look at the user question, and make a decision on
    # whether we want to do simple_recommendation or run_optimizer_model
    res = await make_request(
        DEFOG_BASE_URL + "/oracle/gen_optimization_task",
        data={
            "question": user_question,
            "api_key": api_key,
            "username": username,
            "report_id": report_id,
            "task_type": task_type,
            "gather_context": gather_context,
            "explore": explorer_outputs,
        },
    )

    LOGGER.info(f"Tasks: {json.dumps(res, indent=2)}")

    optimizer_outputs = {}
    optimizer_task_type = res["task_type"]

    if optimizer_task_type == "simple_recommendation":
        processed_items = []

        for item in res["processing_list"]:
            qn_id = item["qn_id"]
            columns = item["columns"]
            aggregations = item["aggregations"]
            explanation = item["explanation"]
            # look for the qn_ids's artifact in the explore's outputs
            relevant_explorer_output = [q for q in analyses if q["qn_id"] == qn_id]
            if len(relevant_explorer_output) == 0:
                LOGGER.error(
                    f"Did not find relevant question requested by optimizer: {item}"
                )
                continue

            relevant_explorer_output = relevant_explorer_output[0]
            table_csv = (
                relevant_explorer_output.get("artifacts", {})
                .get("table_csv", {})
                .get("artifact_content", None)
            )

            if not table_csv:
                LOGGER.error(
                    f"Did not find csv data in the explorer's output: {relevant_explorer_output}"
                )
                continue

            df = pd.read_csv(StringIO(table_csv))

            for col, agg in zip(columns, aggregations):
                col_values = df[col]

                processed = {
                    "qn_id": qn_id,
                    "column": col,
                    "aggregation": agg,
                    "explanation": explanation,
                }

                LOGGER.info("\n\n---\n\n")
                LOGGER.info(f"col: {col}")
                LOGGER.info(f"col_values: {col_values}")
                LOGGER.info(f"agg: {agg}")
                LOGGER.info("\n\n---\n\n")

                if not agg:
                    processed["result"] = col_values.to_csv(index=False)
                elif agg == "mean":
                    processed["result"] = col_values.mean()
                elif agg == "sum":
                    processed["result"] = col_values.sum()
                elif agg == "min":
                    processed["result"] = col_values.min()
                elif agg == "max":
                    processed["result"] = col_values.max()
                elif agg == "variance":
                    processed["result"] = col_values.var()
                elif agg == "count":
                    processed["result"] = len(col_values)
                elif agg == "unique_count":
                    processed["result"] = int(col_values.nunique())
                elif agg == "unique_values":
                    processed["result"] = col_values.unique().to_csv(index=False)
                else:
                    LOGGER.error(f"Could not do aggregation: {agg} for item: {item}")

                processed_items.append(processed)

        optimizer_outputs["processed_items"] = processed_items

        LOGGER.info(processed_items)

        # now using the above processed items
        # get the actual recommendations

        # now construct actual recommendations
        recommendations = await make_request(
            DEFOG_BASE_URL
            + "/oracle/optimization_gen_recommendations_from_simple_analysis",
            data={
                "question": user_question,
                "api_key": api_key,
                "username": username,
                "report_id": report_id,
                "task_type": task_type,
                "gather_context": gather_context,
                "explore": explorer_outputs,
                "processed_items": processed_items,
            },
        )

        LOGGER.info(f"Recommendations: {recommendations}")

    else:
        optimizer_outputs = {}

    return {
        "subtask_type": optimizer_task_type,
        "outputs": optimizer_outputs,
        "recommendations": recommendations,
    }
