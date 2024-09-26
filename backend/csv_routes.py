import os
from fastapi import APIRouter, Request
from generic_utils import get_api_key_from_key_name, make_request
import pandas as pd
from io import StringIO
from fastapi.responses import JSONResponse

router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


@router.post("/generate_column_descriptions_for_csv")
async def generate_column_descriptions_for_csv(request: Request):
    """
    Adds column descriptions to the metadata of a CSV file
    Expects a list of dictionaries with keys 'column_name' and 'data_type'
    Return a list of dictionaries with keys 'column_name', 'data_type', and 'column_description'
    This is done by sending a POST request to the /generate_metadata_csv endpoint
    """
    params = await request.json()
    key_name = params.get("key_name", None)
    metadata = params.get("metadata", None)
    table_name = params.get("table_name", None)

    if not key_name:
        return {"error": "no key name provided"}
    if not metadata:
        return {"error": "no metadata provided"}
    if not table_name:
        return {"error": "no table name provided"}

    api_key = get_api_key_from_key_name(key_name)

    # verify that metadata is a list
    if not isinstance(metadata, list):
        return {"error": "metadata must be a list of dictionaries"}

    # verify that each element in metadata is a dictionary
    for element in metadata:
        if not isinstance(element, dict):
            return {"error": "each element in metadata must be a dictionary"}

    # verify that each dictionary in metadata has the keys 'column_name' and 'data_type'
    for element in metadata:
        if "column_name" not in element:
            return {
                "error": "each dictionary in metadata must have the key 'column_name'"
            }
        if "data_type" not in element:
            return {
                "error": "each dictionary in metadata must have the key 'data_type'"
            }

    # now, send a request to `/get_schema_csv`
    schemas = {table_name: metadata}
    r = await make_request(
        f"{DEFOG_BASE_URL}/get_schema_csv",
        {
            "api_key": api_key,
            "schemas": schemas,
        },
    )
    metadata_csv_string = r["csv"]
    metadata_json = (
        pd.read_csv(StringIO(metadata_csv_string)).fillna("").to_dict(orient="records")
    )
    return metadata_json


@router.post("/generate_query_csv")
async def generate_query_csv(request: Request):
    """
    Generates a CSV file with the results of a query
    Expects a query string
    Return a CSV file with the results of the query
    This is done by sending a POST request to the /generate_query_csv endpoint
    """
    params = await request.json()
    key_name = params.get("key_name", None)
    question = params.get("question", None)
    metadata = params.get("metadata", None)
    previous_questions = params.get("previous_questions", [])

    if len(previous_questions) > 0:
        previous_questions = previous_questions[:-1]

    prev_questions = []
    for item in previous_questions:
        prev_question = item.get("user_question")
        if question:
            prev_steps = (
                item.get("analysisManager", {})
                .get("analysisData", {})
                .get("gen_steps", {})
                .get("steps", [])
            )
            if len(prev_steps) > 0:
                for step in prev_steps:
                    if "sql" in step:
                        prev_sql = step["sql"]
                        prev_questions.append(prev_question)
                        prev_questions.append(prev_sql)
                        break

    # metadata should be a list of dictionaries with keys 'table_name', 'column_name', 'data_type', and 'column_description'\

    if not key_name:
        return {"error": "no key name provided"}
    if not question:
        return {"error": "no question provided"}
    if not metadata:
        return {"error": "no metadata provided"}

    if not isinstance(metadata, list):
        return {"error": "metadata must be a list of dictionaries"}

    for element in metadata:
        if not isinstance(element, dict):
            return {"error": "each element in metadata must be a dictionary"}
        if "table_name" not in element:
            return {
                "error": "each dictionary in metadata must have the key 'table_name'"
            }
        if "column_name" not in element:
            return {
                "error": "each dictionary in metadata must have the key 'column_name'"
            }
        if "data_type" not in element:
            return {
                "error": "each dictionary in metadata must have the key 'data_type'"
            }
        # let's keep column descriptions optional for now
        # if "column_description" not in element:
        #     return {
        #         "error": "each dictionary in metadata must have the key 'column_description'"
        #     }

    api_key = get_api_key_from_key_name(key_name)

    # convert metadata to a dictionary
    metadata_dict = {}
    for element in metadata:
        table_name = element["table_name"]
        if table_name not in metadata_dict:
            metadata_dict[table_name] = []
        metadata_dict[table_name].append(
            {
                "column_name": element["column_name"],
                "data_type": element["data_type"],
                "column_description": element.get("column_description"),
            }
        )

    r = await make_request(
        f"{DEFOG_BASE_URL}/generate_query_chat",
        {
            "api_key": api_key,
            "question": question,
            "metadata": metadata_dict,
            "db_type": "sqlite",
            "previous_context": prev_questions,
        },
    )
    return r


@router.post("/retry_query_csv")
async def generate_query_csv(request: Request):
    """
    Generates a CSV file with the results of a query
    Expects a query string
    Return a CSV file with the results of the query
    This is done by sending a POST request to the /generate_query_csv endpoint
    """
    params = await request.json()
    key_name = params.get("key_name", None)
    question = params.get("question", None)
    metadata = params.get(
        "metadata", None
    )  # metadata should be a list of dictionaries with keys 'table_name', 'column_name', 'data_type', and 'column_description'
    previous_query = params.get("previous_query", None)
    error = params.get("error", None)

    if not key_name:
        return JSONResponse(content={"error": "no key name provided"}, status_code=400)
    if not question:
        return JSONResponse(content={"error": "no question provided"}, status_code=400)
    if not metadata:
        return JSONResponse(content={"error": "no metadata provided"}, status_code=400)
    if not previous_query:
        return JSONResponse(
            content={"error": "no previous query provided"}, status_code=400
        )
    if not error:
        return JSONResponse(content={"error": "no error provided"}, status_code=400)

    api_key = get_api_key_from_key_name(key_name)

    # convert metadata to a dictionary
    metadata_dict = {}
    for element in metadata:
        table_name = element["table_name"]
        if table_name not in metadata_dict:
            metadata_dict[table_name] = []
        metadata_dict[table_name].append(
            {
                "column_name": element["column_name"],
                "data_type": element["data_type"],
                "column_description": element.get("column_description"),
            }
        )

    r = await make_request(
        f"{DEFOG_BASE_URL}/retry_query_after_error",
        {
            "api_key": api_key,
            "question": question,
            "metadata": metadata_dict,
            "db_type": "sqlite",
            "previous_query": previous_query,
            "error": error,
        },
    )
    r["sql"] = r["new_query"]
    del r["new_query"]
    return r
