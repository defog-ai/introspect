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

    return {
        "analysis": "",
        "outputs": [{"data": df}],
        "sql": query,
    }
