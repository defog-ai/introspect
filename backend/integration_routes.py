from fastapi import APIRouter, Request
import json
import os
from defog import Defog
from io import StringIO
from defog.query import execute_query
import re
import pandas as pd
from fastapi.responses import JSONResponse
from uuid import uuid4

from db_utils import (
    validate_user,
    get_db_type_creds,
    update_db_type_creds,
    save_csv_to_db,
)
import asyncio
from generic_utils import (
    make_request,
    convert_nested_dict_to_list,
    get_api_key_from_key_name,
)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
print(DEFOG_BASE_URL, flush=True)

home_dir = os.path.expanduser("~")
defog_path = os.path.join(home_dir, ".defog")

# create defog_path if it doesn't exist
if not os.path.exists(defog_path):
    os.makedirs(defog_path)

router = APIRouter()


@router.post("/integration/get_tables_db_creds")
async def get_tables_db_creds(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)

    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    try:
        defog = Defog(api_key=api_key, db_type=db_type, db_creds=db_creds)
        defog.base_url = DEFOG_BASE_URL
    except:
        return {"error": "no defog instance found"}

    try:
        table_names = await asyncio.to_thread(
            defog.generate_db_schema,
            tables=[],
            upload=False,
            scan=False,
            return_tables_only=True,
        )
        print(table_names, flush=True)
    except Exception as e:
        print(e, flush=True)
        table_names = []

    try:
        with open(
            os.path.join(defog_path, f"selected_tables_{api_key}.json"), "r"
        ) as f:
            selected_table_names = json.load(f)
            if not selected_table_names:
                raise Exception("No selected tables found")
    except:
        selected_table_names = table_names

    # only keep selected table names that are in table_names
    selected_table_names = [t for t in selected_table_names if t in table_names]

    db_type = defog.db_type
    db_creds = defog.db_creds

    return {
        "tables": table_names,
        "db_creds": db_creds,
        "db_type": db_type,
        "selected_tables": selected_table_names,
    }


@router.post("/integration/get_metadata")
async def get_metadata(request: Request):
    params = await request.json()
    token = params.get("token")
    is_temp = params.get("temp", False)
    if not validate_user(token):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)

    try:
        md = await make_request(
            f"{DEFOG_BASE_URL}/get_metadata", {"api_key": api_key, "temp": is_temp}
        )
        table_metadata = md["table_metadata"]

        metadata = convert_nested_dict_to_list(table_metadata)
        return {"metadata": metadata}
    except:
        return {"error": "no metadata found"}


@router.post("/integration/validate_db_connection")
async def validate_db_connection(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    db_type = params.get("db_type")
    db_creds = params.get("db_creds")
    for k in ["api_key", "db_type"]:
        if k in db_creds:
            del db_creds[k]

    if db_type == "bigquery":
        db_creds["json_key_path"] = "./bq.json"

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    sql_query = "SELECT 'test';"
    try:
        await asyncio.to_thread(
            execute_query,
            sql_query,
            api_key,
            db_type,
            db_creds,
            retries=0,
        )
        return {"status": "success"}
    except Exception as e:
        print(e, flush=True)
        return {
            "status": "error",
            "message": "Could not connect to the database within 10 seconds. Please verify that the DB credentials are correct.",
        }


@router.post("/integration/update_db_creds")
async def update_db_creds(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)

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

    success = update_db_type_creds(api_key=api_key, db_type=db_type, db_creds=db_creds)
    print(success)

    return {"success": True}


@router.post("/integration/generate_metadata")
async def generate_metadata(request: Request):
    params = await request.json()

    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    tables = params.get("tables")
    dev = params.get("dev", False)

    with open(os.path.join(defog_path, f"selected_tables_{api_key}.json"), "w") as f:
        json.dump(tables, f)

    defog = Defog(api_key=api_key, db_type=db_type, db_creds=db_creds)
    defog.base_url = DEFOG_BASE_URL

    # ugly hack here for now
    # need to fix in defog-python later
    schemas = []
    for table in tables:
        if "." in table:
            if table.split(".")[0] not in schemas:
                schemas.append(table.split(".")[0])
        else:
            if "public" not in schemas:
                schemas.append("public")

    print(schemas)
    print(tables)

    if schemas != ["public"] and defog.db_type == "postgres":
        table_metadata = await asyncio.to_thread(
            defog.generate_postgres_schema,
            tables=tables,
            schemas=schemas,
            upload=False,
            scan=False,
        )
    else:
        table_metadata = await asyncio.to_thread(
            defog.generate_db_schema,
            tables=tables,
            upload=False,
            scan=False,
        )

    md = await make_request(
        f"{DEFOG_BASE_URL}/get_metadata", {"api_key": api_key, "dev": dev}
    )
    print("here 3")
    try:
        existing_metadata = md["table_metadata"]
    except:
        print("No existing metadata found", flush=True)
        existing_metadata = {}

    for table_name in table_metadata:
        for idx, item in enumerate(table_metadata[table_name]):
            if table_name in existing_metadata:
                print(f"Found table {table_name} in existing metadata", flush=True)
                for existing_item in existing_metadata[table_name]:
                    if existing_item["column_name"] == item["column_name"]:
                        print(
                            f"Found column {item['column_name']} in existing metadata",
                            flush=True,
                        )
                        table_metadata[table_name][idx]["column_description"] = (
                            existing_item["column_description"]
                        )

    metadata = convert_nested_dict_to_list(table_metadata)
    return {"metadata": metadata}


@router.post("/integration/update_metadata")
async def update_metadata(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    metadata = params.get("metadata")
    dev = params.get("dev", False)

    # convert metadata to nested dictionary
    table_metadata = {}
    for item in metadata:
        table_name = item["table_name"]
        if table_name not in table_metadata:
            table_metadata[table_name] = []
        table_metadata[table_name].append(
            {
                "column_name": item["column_name"],
                "data_type": item["data_type"],
                "column_description": item["column_description"],
            }
        )

    # update on API server
    r = await make_request(
        DEFOG_BASE_URL + "/update_metadata",
        json={
            "api_key": api_key,
            "table_metadata": table_metadata,
            "db_type": db_type,
            "dev": dev,
        },
    )

    return r


@router.post("/integration/copy_prod_to_dev")
async def copy_prod_to_dev(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)

    r = await make_request(
        DEFOG_BASE_URL + "/copy_prod_to_dev", json={"api_key": api_key}
    )

    return r


@router.post("/integration/copy_dev_to_prod")
async def copy_prod_to_dev(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)

    r = await make_request(
        DEFOG_BASE_URL + "/copy_dev_to_prod", json={"api_key": api_key}
    )

    return r


@router.post("/integration/get_glossary_golden_queries")
async def get_glossary_golden_queries(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev", False)
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    defog = Defog(api_key, db_type, db_creds)
    defog.base_url = DEFOG_BASE_URL

    # get glossary
    url = DEFOG_BASE_URL + "/get_glossary"
    resp = await make_request(url, {"api_key": api_key, "dev": dev})
    resp = resp.get("glossary", {})

    # get golden queries
    golden_queries = await asyncio.to_thread(defog.get_golden_queries, dev=dev)

    # for backwards compatibility
    glossary = resp.get("glossary", "")
    glossary_compulsory = resp.get("glossary_compulsory", "")
    glossary_prunable_units = resp.get("glossary_prunable_units", [])
    glossary_prunable_units = "\n".join(glossary_prunable_units)
    # for backwards compatibility
    # if `glossary` is non empty and glossary compulsory is empty, set glossary compulsory to glossary
    if glossary_compulsory == "" and glossary != "":
        glossary_compulsory = glossary

    return {
        "glossary_compulsory": glossary_compulsory,
        "glossary_prunable_units": glossary_prunable_units,
        "golden_queries": golden_queries,
    }


@router.post("/integration/update_glossary")
async def update_glossary(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    append = params.get("append", False)

    if not append:
        # completely overwrite the existing glossary
        glossary_compulsory = params.get("glossary_compulsory")
        glossary_prunable_units = params.get("glossary_prunable_units")
        dev = params.get("dev", False)

        if glossary_prunable_units:
            glossary_prunable_units = glossary_prunable_units.split("\n")

        defog = Defog(api_key=api_key, db_type=db_type, db_creds=db_creds)
        defog.base_url = DEFOG_BASE_URL

        # update glossary
        r = await asyncio.to_thread(
            defog.update_glossary,
            glossary_compulsory=glossary_compulsory,
            glossary_prunable_units=glossary_prunable_units,
            dev=dev,
        )
    else:
        # first, get the existing glossary
        url = DEFOG_BASE_URL + "/get_glossary"
        resp = await make_request(url, {"api_key": api_key, "dev": dev})
        resp = resp.get("glossary", {})
        glossary = resp.get("glossary", "")
        glossary_compulsory = resp.get("glossary_compulsory", "")
        glossary_prunable_units = resp.get("glossary_prunable_units", [])
        # for backwards compatibility
        # if `glossary` is non empty and glossary compulsory is empty, set glossary compulsory to glossary
        if glossary_compulsory == "" and glossary != "":
            glossary_compulsory = glossary

        new_instructions = params.get("new_instructions")
        if new_instructions:
            glossary_prunable_units += new_instructions.split("\n")

        dev = params.get("dev", False)

        defog = Defog(api_key=api_key, db_type=db_type, db_creds=db_creds)
        defog.base_url = DEFOG_BASE_URL

        # update glossary
        r = await asyncio.to_thread(
            defog.update_glossary,
            glossary_compulsory=glossary_compulsory,
            glossary_prunable_units=glossary_prunable_units,
            dev=dev,
        )
    return r


@router.post("/integration/update_golden_queries")
async def update_golden_queries(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    golden_queries = params.get("golden_queries")
    dev = params.get("dev", False)

    defog = Defog(api_key=api_key, db_type=db_type, db_creds=db_creds)
    defog.base_url = DEFOG_BASE_URL

    # first, delete the existing golden queries
    r = await asyncio.to_thread(
        defog.delete_golden_queries,
        all=True,
        dev=dev,
    )

    # update golden queries
    r = await asyncio.to_thread(
        defog.update_golden_queries, golden_queries, dev=dev, scrub=False
    )
    return r


@router.post("/integration/upload_csv")
async def upload_csv(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name", params.get("keyName"))
    if not key_name:
        print("No key name found", flush=True)
        print("Defaulting to first key name", flush=True)
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    data = params.get("data", [])

    defog = Defog(
        api_key=api_key,
        db_type=db_type,
        db_creds={
            "host": "agents-postgres",
            "port": 5432,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres",
        },
    )
    defog.base_url = DEFOG_BASE_URL

    # save the csv file as a table to the local database
    save_csv_to_db(
        table_name="temp_table",
        data=data,
    )

    csv = await asyncio.to_thread(
        defog.generate_db_schema,
        tables=["temp_table"],
        upload=True,
        scan=False,
        return_format="other",
    )

    schema_df = pd.read_csv(StringIO(csv))
    schema_df.dropna(subset=["column_name"], inplace=True)
    schema_df.fillna("", inplace=True)
    schema = {}
    for table_name in schema_df["table_name"].unique():
        schema[table_name] = schema_df[schema_df["table_name"] == table_name][
            ["column_name", "data_type", "column_description"]
        ].to_dict(orient="records")

    resp = await make_request(
        DEFOG_BASE_URL + "/update_metadata",
        json={
            "api_key": api_key,
            "table_metadata": schema,
            "db_type": db_type,
            "temp": True,
            "dev": False,
        },
    )

    print("reached the upload_csv route", flush=True)
    return resp


@router.post("/integration/preview_table")
async def preview_table(request: Request):
    """
    Preview the first 10 rows of a table, given the table name and standard parameters of token, key_name, and temp
    Also sanitizes the table name to prevent SQL injection
    KNOWN ISSUE: Does not work if the table name has a double quote in it
    """
    params = await request.json()
    token = params.get("token")
    if not validate_user(token):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
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
        res = get_db_type_creds(api_key)
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
    if db_type not in ["sqlserver", "bigquery"]:
        sql_query = f'SELECT * FROM "{table_name}" LIMIT 10'
    elif db_type == "sqlserver":
        sql_query = f'SELECT TOP 10 * FROM "{table_name}"'
    elif db_type == "bigquery":
        sql_query = f"SELECT * FROM `{table_name}` LIMIT 10"

    print("Executing preview table query", flush=True)
    print(sql_query, flush=True)

    try:
        colnames, data, _ = await asyncio.to_thread(
            execute_query, sql_query, api_key, db_type, db_creds, retries=0, temp=temp
        )
    except:
        return {"error": "error executing query"}

    return {"data": data, "columns": colnames}


@router.post("/integration/get_dynamic_glossary")
async def get_dynamic_glossary(request: Request):
    params = await request.json()
    token = params.get("token")
    if not validate_user(token):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    dev = params.get("dev", False)
    question = params.get("question")

    r = await make_request(
        DEFOG_BASE_URL + "/prune_glossary",
        {"question": question, "api_key": api_key, "dev": dev},
    )

    return r
