import traceback
from agents.planner_executor.tool_helpers.core_functions import (
    safe_sql,
    fetch_query_into_df,
)
from utils import error_str
import asyncio
import requests


async def data_fetcher_and_aggregator(
    question: str,
    limit_rows: bool = False,
    global_dict: dict = {},
    **kwargs,
):
    """
    This function generates a SQL query and runs it to get the answer.
    """
    glossary = global_dict.get("glossary", "")
    metadata = global_dict.get("table_metadata_csv", "")

    # send the data to an API, and get a response from it
    url = "https://defog-llm-calls-ktcmdcmg4q-uc.a.run.app"
    payload = {
        "request_type": "generate_sql",
        "question": question,
        "glossary": glossary,
        "metadata": metadata,
    }

    # make async request to the url, using the appropriate library
    r = await asyncio.to_thread(requests.post, url, json=payload)
    res = r.json()
    query = res["query"]

    if not safe_sql(query):
        success = False
        print("Unsafe SQL Query")

    print(f"Running query: {query}")

    df = await fetch_query_into_df(query)

    analysis = ""

    # if total number of cells in the df < 50, run an analysis
    # if df.size < 50:
    #     try:
    #         payload = {
    #             "request_type": "analyze_data",
    #             "question": question,
    #             # decimals at 0.3f
    #             "data": df.to_json(orient="split", double_precision=5),
    #         }
    #         analysis = await asyncio.to_thread(requests.post, url, json=payload)

    #         analysis = analysis.json()
    #         analysis = analysis["model_analysis"]
    #     except Exception as e:
    #         print(f"Error in running analysis: {e}")
    #         traceback.print_exc()
    #         analysis = ""
    # else:
    #     analysis = ""

    return {
        "outputs": [{"data": df, "analysis": analysis}],
        "sql": query.strip(),
    }
