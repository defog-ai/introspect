import asyncio
import json
import os
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from utils_logging import LOGGER
from utils_sql import compare_query_results
from generic_utils import  format_sql
import pandas as pd
from asyncio import Semaphore
from defog import AsyncDefog
from utils_sql import generate_sql_query
from tool_code_utilities import fetch_query_into_df

test_query_semaphore = Semaphore(5)
run_query_semaphore = Semaphore(3)


async def run_query(
    db_name: str, question: str, db_type: str, previous_context: list[str] = []
):
    """
    Send the data to the Defog servers, and get a response from it.
    """
    # make async request to the url, using the appropriate library
    res = await generate_sql_query(
        db_name=db_name,
        question=question,
        db_type=db_type,
        previous_context=previous_context
    )
    return res


async def test_query(
    db_name: str,
    db_type: str,
    db_creds: Dict[str, str],
    question: str,
    original_sql: str = None,
    previous_context: list[str] = [],
    query_id: str = None,
) -> Dict[str, Any]:
    """
    Test the generated SQL for the given question.
    Returns the result of the comparison between the golden query and the generated query.
    """
    # we want to use the Defog client, so that we get the SQL *after* all error correction
    # and so that it works regardless of the db type
    # we also want to be loudly notified on Slack if the SQL generation fails for this api key

    async with test_query_semaphore:
        res = await generate_sql_query(
            question=question,
            db_name=db_name,
            previous_context=previous_context
        )

        sql_gen = res["sql"]
        # df_gen = pd.DataFrame(res["data"], columns=res["columns"])

        df_gen, sql_gen = await fetch_query_into_df(
            db_name=db_name,
            sql_query=sql_gen,
            question=question,
        )

        result = await compare_query_results(
            query_gold=original_sql,
            query_gen=sql_gen,
            df_gen=df_gen,
            question=question,
            db_type=db_type,
            db_creds=db_creds,
        )

        result["model_sql"] = format_sql(sql_gen)

        result["question"] = question
        result["original_sql"] = format_sql(original_sql)

        result["query_id"] = query_id or str(uuid4())

        LOGGER.debug(f"\n[RegressionTesting] - Question: {question}")
        LOGGER.debug(
            f"\n[RegressionTesting] - Previous context: {json.dumps(previous_context, indent=2)}"
        )
        LOGGER.debug(f"\n[RegressionTesting] - Original SQL: {original_sql}")
        LOGGER.debug(f"\n[RegressionTesting] - Generated SQL: {sql_gen}")

        return result


async def validate_queries(
    api_key: str,
    db_type: str,
    db_creds: Dict[str, str],
    queries: list[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Validates the given queries/query pairs. Checking if the model generated sql is correct or not.

    `queries` is a list of objects, each with the following keys:
    - queries: list[str] - A list of queries. All but last are used as `previous_context`. The last item in the array is used as the main question.
    - sql: str - The correct SQL to check against.
    """
    num_correct = 0
    tasks = []
    query_wise_results = {}

    for query in queries:
        # queries have a questions array
        # we use all till -1 as previous_context
        if not len(query["questions"]):
            continue

        # note that this only the questions, NOT the SQL
        previous_questions = query["questions"][:-1]
        question = query["questions"][-1]
        original_sql = query["sql"]

        query_id = query.get("id") or str(uuid4())
        sqls_generated = []

        # this will be an alternating array of question, sql
        # we can only run these questions one by one because final question's answer depend on previous ones' outputs
        previous_context = []

        for q in previous_questions:
            res = await run_query(
                api_key=api_key,
                question=q,
                db_type=db_type,
                previous_context=previous_context,
            )

            sql = res.get("sql")

            if sql is None:
                raise ValueError(
                    f"Error in generating query for question: {q}, which was part of the previous context for question: {question}.\nFull input: {query}"
                )

            LOGGER.info(f"[RegressionTesting] - Question: {q}")
            LOGGER.info(f"[RegressionTesting] - SQL: {sql}")

            previous_context += [q, sql]
            sqls_generated += [q, sql]

        query_wise_results[query_id] = {
            "question": question,
            "original_sql": original_sql,
            "previous_questions_sql": sqls_generated,
            "correct": False,
            "subset": False,
        }

        test_query_task = test_query(
            api_key=api_key,
            db_type=db_type,
            db_creds=db_creds,
            question=question,
            original_sql=original_sql,
            previous_context=previous_context,
            query_id=query_id,
        )
        tasks.append(test_query_task)

    # and run them together all at once
    results = await asyncio.gather(*tasks)
    for result in results:
        if result.get("correct"):
            num_correct += 1
        if result.get("query_id") in query_wise_results:
            query_wise_results[result["query_id"]].update(result)

    return {
        "total": len(results),
        "correct": num_correct,
        "results": results,
        "query_wise_results": query_wise_results,
    }
