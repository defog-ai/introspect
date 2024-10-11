import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from db_utils import INTERNAL_DB
from generic_utils import make_request
from utils_imported_data import (
    IMPORTED_SCHEMA,
    update_imported_tables,
    update_imported_tables_db,
)
from utils_logging import LOGGER

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
router = APIRouter()

@router.post("/import_table/create")
async def import_table_route(request: Request):
    """
    [Testing]
    Route for importing a table from the request body into the imported database

    Context:
    To import data into the imported_tables database, we need to do 3 things:
    1. Insert the data into the imported_tables database as a new table.
        This is done by calling the `update_imported_tables_db` function.
        It will update if the data's origin already exists in the database.
    2. Insert the data's origin into the imported_tables database.
        We need to keep track of each's data origin to be able to update the data
        based on the origin later. E.g. if the 2nd table from a link is updated,
        we want to know what the old table name was and delete that, before inserting
        the new data and updating the imported_tables table.
    3. Infer the column types/descriptions from the data.
    4. Get and update the metadata to and from defog.

    # Input format
    {
        "api_key": "123",
        "data": [
            ["product_name", "price", "quantity", "date_purchased", "card_number"],
            ["apple", "1.00", "5", "2021-01-01", "4111111111111111"],
            ["banana", "0.50", "10", "2021-01-02", "378282246310005"],
            ["cherry", "2.00", "3", "2021-01-03", "6011000990139424"],
        ],
        "link": "https://example.com",
        "table_index": 0,
        "table_name": "fruit_products",
        "table_description": "This table contains fruit products purchased by certain card numbers"
    }
    """
    body = await request.json()
    LOGGER.debug(f"Import table request body: {body}")
    api_key = body.get("api_key")
    data = body.get("data") # csv, includes columns in first row
    link = body.get("link")
    table_index = int(body.get("table_index", 0))
    table_name = body.get("table_name")
    table_description = body.get("table_description", "")

    schema = body.get("schema", IMPORTED_SCHEMA)
    success, old_table_name = update_imported_tables_db(
        link=link,
        table_index=table_index,
        new_table_name=table_name,
        data=data,
        schema_name=schema,
    )
    if not success:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to update imported tables database",
            },
        )
    LOGGER.debug(f"Updated imported tables database with table: {table_name}")
    LOGGER.debug(f"Old table name: {old_table_name}")

    success = update_imported_tables(
        link=link,
        table_index=table_index,
        old_table_name=old_table_name,
        table_name=table_name,
        table_description=table_description,
    )
    if not success:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to update imported tables database with the table origin",
            },
        )
    infer_request = {
        "api_key": api_key,
        "all_rows": data,
        "previous_text": None,
    }
    try:
        table_properties = await make_request(
            DEFOG_BASE_URL + "/unstructured_data/infer_table_properties",
            infer_request,
        )
    except Exception as e:
        LOGGER.error(f"Failed to infer table properties: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to infer table properties",
            },
        )
    if "columns" not in table_properties or "table_name" not in table_properties:
        LOGGER.error(f"No columns or table name in table properties: {table_properties}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to infer table properties",
            },
        )
    if len(table_properties["columns"]) != len(data[0]):
        LOGGER.error(f"Number of columns in table properties does not match data: {table_properties}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to infer table properties",
            },
        )
    md_new_table = {
        table_properties["table_name"]: table_properties["columns"],
    }
    # TODO get imported metadata from defog, delete old table, insert new table
    try:
        response = await make_request(
            url=f"{DEFOG_BASE_URL}/get_metadata", 
            data={"api_key": api_key, "imported": True},
        )
        md = response.get("table_metadata", {})
        if old_table_name and old_table_name in md:
            del md[old_table_name]
        md.update(md_new_table)
        update_request = {
            "api_key": api_key,
            "table_metadata": md,
            "imported": True,
            "db_type": INTERNAL_DB
        }
        response = await make_request(
            url=f"{DEFOG_BASE_URL}/update_metadata", 
            data=update_request,
        )
    except Exception as e:
        LOGGER.error(f"Failed to get and update metadata: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to get and update metadata",
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "message": "Table imported successfully",
            "table_name": table_name,
        },
    )
    
