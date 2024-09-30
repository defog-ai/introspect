import asyncio
import os
from typing import Any, Dict, List, Tuple

from utils_sql import compare_query_results
from generic_utils import make_request
from oracle.utils_explore_data import gen_sql

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


async def test_query(
    api_key: str,
    db_type: str,
    db_creds: Dict[str, str],
    question: str,
    original_sql: str,
    source: str,
) -> Dict[str, Any]:
    """
    Test the generated SQL for the given question.
    Returns the result of the comparison between the golden query and the generated query.
    """
    sql_gen = await gen_sql(api_key, db_type, question, None)
    result = await compare_query_results(
        original_sql, sql_gen, question, api_key, db_type, db_creds
    )
    result["question"] = question
    result["sql_golden"] = original_sql
    result["sql_gen"] = sql_gen
    result["source"] = source
    return result


async def validate_queries(
    api_key: str, db_type: str, db_creds: Dict[str, str]
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Validate the golden queries for the given api_key.
    Returns the correct and subset-correct rates of the golden queries along
    with a list of golden queries that were incorrect.
    """
    data = {"api_key": api_key}
    golden_queries_task = make_request(f"{DEFOG_BASE_URL}/get_golden_queries", data)
    feedback_task = make_request(f"{DEFOG_BASE_URL}/get_feedback", data)
    golden_queries_response, feedback_response = await asyncio.gather(
        golden_queries_task, feedback_task
    )
    # create tasks from both the golden queries and the positive feedback
    golden_queries = golden_queries_response.get("golden_queries", [])
    num_correct = 0
    num_subset = 0
    tasks = []
    for golden_query in golden_queries:
        if not golden_query.get("user_validated", False):
            continue
        test_query_task = test_query(
            api_key,
            db_type,
            db_creds,
            golden_query["question"],
            golden_query["sql"],
            "golden",
        )
        tasks.append(test_query_task)
    for feedback in feedback_response.get("data", []):
        if str(feedback[1]).lower() == "good":
            test_query_task = test_query(
                api_key, db_type, db_creds, feedback[2], feedback[3], "feedback"
            )
            tasks.append(test_query_task)
    # and run them together all at once
    results = await asyncio.gather(*tasks)
    for result in results:
        if result["correct"]:
            num_correct += 1
        if result["subset"]:
            num_subset += 1
    return (
        num_correct / len(results),
        num_subset / len(results),
        results,
    )
