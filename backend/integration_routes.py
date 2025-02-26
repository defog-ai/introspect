import asyncio
import json
import os
import re
from io import StringIO
import traceback
from uuid import uuid4
import pandas as pd
from db_utils import (
    get_db_info,
    get_db_type_creds,
    update_db_type_creds,
    validate_db_connection,
)
from db_config import redis_client
from auth_utils import validate_user, validate_user_request
from defog import Defog
from defog.query import async_execute_query_once
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from request_models import UserRequest
from utils_logging import LOGGER
from utils_md import check_metadata_validity, get_metadata, set_metadata

home_dir = os.path.expanduser("~")
defog_path = os.path.join(home_dir, ".defog")

# create defog_path if it doesn't exist
if not os.path.exists(defog_path):
    os.makedirs(defog_path)

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Metadata Management"],
)


@router.post("/integration/get_db_info")
async def get_tables_db_creds(req: UserRequest):
    try:
        db_info = await get_db_info(req.db_name)

        return JSONResponse(
            content=db_info,
            status_code=200,
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/integration/update_db_creds")
async def update_db_creds(request: Request):
    params = await request.json()
    db_name = params.get("db_name")
    db_type = params.get("db_type")
    db_creds = params.get("db_creds")
    for k in ["api_key", "db_type"]:
        if k in db_creds:
            del db_creds[k]

    if db_type == "bigquery":
        credentials_file = db_creds.get("credentials_file_content")
        if credentials_file:
            del db_creds["credentials_file_content"]
            fname = str(uuid4()) + ".json"
            with open(os.path.join(defog_path, fname), "w") as f:
                f.write(credentials_file)
        db_creds["json_key_path"] = os.path.join(defog_path, fname)

    try:
        await update_db_type_creds(db_name=db_name, db_type=db_type, db_creds=db_creds)

        # send back latest full info
        db_info = await get_db_info(db_name=db_name)

        return JSONResponse(
            content=db_info,
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(
            {
                "status": "error",
                "message": "Could not update the database credentials. Please try again.",
            },
            status_code=400,
        )


@router.post("/integration/preview_table")
async def preview_table(request: Request):
    """
    Preview the first 10 rows of a table, given the table name and standard parameters of token, db_name, and temp
    Also sanitizes the table name to prevent SQL injection
    KNOWN ISSUE: Does not work if the table name has a double quote in it
    """
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    db_name = params.get("db_name")
    temp = params.get("temp", False)
    if temp:
        db_type = "postgres"
        table_name = "temp_table"
        db_creds = {
            "host": "agents-postgres",
            "port": 5432,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres",
        }
    else:
        res = await get_db_type_creds(db_name)
        if res:
            db_type, db_creds = res
        else:
            return {"error": "no db creds found"}

        table_name = params.get("table_name")

    print("Table name", table_name, flush=True)
    print("DB Type", db_type, flush=True)

    # we need to sanitize the table name to prevent SQL injection
    # for example, if table_name is `table1; DROP TABLE table2`, and we are just doing `SELECT * FROM {table_name} LIMIT 10`, the query would be "SELECT * FROM table1; DROP TABLE table2 LIMIT 10"
    # to prevent this, we need to check that the table name only has alphanumeric characters, underscores, or spaces
    # further, we will also add quotes around the table name to prevent SQL injection using a space in the table name

    # check that the table name only has alphanumeric characters, underscores, spaces, or periods
    # use regex for this
    if not re.match(r"^[\w .-]+$", table_name):
        # \w: Matches any word character. A word character is defined as any alphanumeric character plus the underscore (a-z, A-Z, 0-9, _).
        # the space after \w is intentional, to allow spaces in the table name
        return {"error": "invalid table name"}

    # in these select statements, add quotes around the table name to prevent SQL injection using a space in the table name
    if "." not in table_name:
        table_name = f'"{table_name}"'
    else:
        table_name = ".".join([f'"{t}"' for t in table_name.split(".")])
    if db_type not in ["sqlserver", "bigquery"]:
        sql_query = f"SELECT * FROM {table_name} LIMIT 10"
    elif db_type == "sqlserver":
        sql_query = f"SELECT TOP 10 * FROM {table_name}"
    elif db_type == "bigquery":
        sql_query = f"SELECT * FROM `{table_name}` LIMIT 10"

    try:
        colnames, data = await async_execute_query_once(db_type, db_creds, sql_query)
    except Exception as e:
        return {"error": f"Error executing query: {str(e)}"}

    return {"data": data, "columns": colnames}


@router.post("/integration/upload_metadata")
async def upload_metadata(request: Request):
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    db_name = params.get("db_name")
    res = await get_db_type_creds(db_name)
    if res:
        db_type, _ = res
    else:
        return {"error": "no db creds found"}

    metadata_csv = params.get("metadata_csv")
    metadata_list = (
        pd.read_csv(StringIO(metadata_csv)).fillna("").to_dict(orient="records")
    )

    # check if metadata is valid
    md_err = check_metadata_validity(table_metadata=metadata_list, db_type=db_type)
    if md_err:
        return JSONResponse(
            {
                "status": "error",
                "message": f"Metadata is not valid for the given database type. {md_err}",
                "error": f"Metadata is not valid for the given database type. {md_err}",
            },
            status_code=400,
        )

    # update on API server
    await set_metadata(db_name=db_name, table_metadata=metadata_list)

    db_info = await get_db_info(db_name)

    return JSONResponse(status_code=200, content=db_info)


@router.post("/integration/get_bedrock_analysis_params")
async def get_bedrock_analysis_params(request: Request):
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    bedrock_model_id = redis_client.get("bedrock_model_id")
    bedrock_model_prompt = redis_client.get("bedrock_model_prompt")

    if not bedrock_model_id:
        bedrock_model_id = "meta.llama3-70b-instruct-v1:0"

    if not bedrock_model_prompt:
        bedrock_model_prompt = """<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Can you please give me the high-level trends (as bullet points that start with a hyphen) of data in a CSV? Note that this CSV was generated to answer the question: `{question}`

This was the SQL query used to generate the table:
{sql}

This was the data generated:
{data_csv}

Do not use too much math in your analysis. Just tell me, at a high level, what the key insights are. Give me the trends as bullet points. No preamble or anything else.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

Here is a summary of the high-level trends in the data:
"""

    return {
        "bedrock_model_id": bedrock_model_id,
        "bedrock_model_prompt": bedrock_model_prompt,
    }


@router.post("/integration/set_bedrock_analysis_params")
async def set_bedrock_analysis_params(request: Request):
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    bedrock_model_id = params.get("bedrock_model_id")
    bedrock_model_prompt = params.get("bedrock_model_prompt")
    redis_client.set(
        f"bedrock_model_id",
        bedrock_model_id,
    )

    redis_client.set(
        f"bedrock_model_prompt",
        bedrock_model_prompt,
    )

    return {"status": "success"}


@router.post("/integration/get_openai_analysis_params")
async def get_openai_analysis_params(request: Request):
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    openai_system_prompt = redis_client.get("openai_system_prompt")
    openai_user_prompt = redis_client.get("openai_user_prompt")

    if not openai_system_prompt:
        openai_system_prompt = """You are a data scientist. You have been given a CSV file with data. You need to analyze the data and provide a summary of the key insights. Please make sure that the summary is concise and to the point, and that you do not make any factual errors."""

    if not openai_user_prompt:
        openai_user_prompt = """A user asked me the question `{question}`. I created the following CSV file to answer the question:
```csv
{data_csv}
```

I also ran the following SQL query to generate the data for this CSV:
```sql
{sql}
```

Please analyze the data in the CSV file and provide a summary of the key insights. Make sure that the summary is concise and to the point, and that you do not make any factual errors. Please give rich, narrative insights that are easy to understand. Do not use too much math in your analysis. Just tell me, at a high level, what the key insights are."""

    return {
        "openai_system_prompt": openai_system_prompt,
        "openai_user_prompt": openai_user_prompt,
    }


@router.post("/integration/set_openai_analysis_params")
async def set_openai_analysis_params(request: Request):
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    openai_system_prompt = params.get("openai_system_prompt")
    openai_user_prompt = params.get("openai_user_prompt")
    redis_client.set(
        "openai_system_prompt",
        openai_system_prompt,
    )

    redis_client.set(
        "openai_user_prompt",
        openai_user_prompt,
    )

    return {"status": "success"}
