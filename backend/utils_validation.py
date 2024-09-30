import os
from typing import Any, Dict, List, Tuple

from utils_sql import compare_query_results
from generic_utils import make_request
from oracle.utils_explore_data import gen_sql

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


async def validate_golden_queries(
    api_key: str, db_type: str, db_creds: Dict[str, str]
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Validate the golden queries for the given api_key.
    Returns the correct and subset-correct rates of the golden queries along
    with a list of golden queries that were incorrect.
    """
    data = {"api_key": api_key}
    response = await make_request(f"{DEFOG_BASE_URL}/get_golden_queries", data)
    golden_queries = response.get("golden_queries", [])
    if not golden_queries:
        return (0.0, 0.0, [])
    num_correct = 0
    num_subset = 0
    validated_golden_queries = []
    for golden_query in golden_queries:
        sql_gen = await gen_sql(api_key, db_type, golden_query["question"], None)
        (correct, subset) = await compare_query_results(
            golden_query["sql"],
            sql_gen,
            golden_query["question"],
            api_key,
            db_type,
            db_creds,
        )
        num_correct += int(correct)
        num_subset += int(subset)
        gq = {
            "question": golden_query["question"],
            "sql_golden": golden_query["sql"],
            "sql_gen": sql_gen,
            "correct": correct,
            "subset": subset,
        }
        validated_golden_queries.append(gq)
    return (
        num_correct / len(golden_queries),
        num_subset / len(golden_queries),
        validated_golden_queries,
    )
