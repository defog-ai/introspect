import asyncio
import datetime
import json
import os
import time
import traceback
from typing import Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from db_utils import (
    INTERNAL_DB,
    ImportedTables,
    OracleSources,
    engine,
    imported_tables_engine,
    validate_user,
)
from generic_utils import get_api_key_from_key_name, make_request
from utils_imported_data import (
    IMPORTED_SCHEMA,
    get_source_type,
    update_imported_tables,
    update_imported_tables_db,
)
from pydantic import BaseModel
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.orm import Session
from utils_imported_data import IMPORTED_SCHEMA
from utils_logging import LOGGER, save_and_log, save_timing


DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
router = APIRouter()


class SourcesListRequest(BaseModel):
    token: str
    key_name: str
    preview_rows: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"token": "user_token", "key_name": "source_key", "preview_rows": 10}
            ]
        }
    }


@router.post("/sources/list")
async def sources_list_route(req: SourcesListRequest):
    """
    List all the sources and their imported tables from the imported_tables database,
    namely where the data was taken from and the table name and description.
    Returns a dictionary of sources with the link as the key and the source title,
    type, summary, and tables as the value.
    """
    if not (await validate_user(req.token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(req.key_name)
    sources = {}
    # get all sources for api_key from engine
    async with engine.connect() as connection:
        stmt_sources = select(OracleSources).where(OracleSources.api_key == api_key)
        result_sources = await connection.execute(stmt_sources)
        result_sources = result_sources.fetchall()
        for source in result_sources:
            sources[source.link] = {
                "source_title": source.title,
                "source_type": source.source_type,
                "source_summary": source.text_summary,
                "tables": [],
            }
    source_links = list(sources.keys())
    # get all imported tables where api_key matches and link is in source_links
    with imported_tables_engine.connect() as connection:
        stmt_list = (
            select(ImportedTables)
            .where(
                ImportedTables.api_key == api_key,
                ImportedTables.table_link.in_(source_links),
            )
            .order_by(ImportedTables.table_link, ImportedTables.table_position)
        )
        result_list = connection.execute(stmt_list)
        imported_tables = result_list.fetchall()
        LOGGER.debug(f"{len(imported_tables)} imported tables found")
        for table in imported_tables:
            table_name = str(table.table_name)
            if not table_name.startswith(IMPORTED_SCHEMA):
                LOGGER.error(
                    f"Table name `{table_name}` does not start with `{IMPORTED_SCHEMA}`."
                )
                continue
            LOGGER.debug(f"Fetching head for table: {table_name}")
            if req.preview_rows:
                stmt_head = text(f"SELECT * FROM {table_name} LIMIT {req.preview_rows}")
            else:
                stmt_head = text(f"SELECT * FROM {table_name}")
            result_head = connection.execute(stmt_head)
            data_head = result_head.fetchall()
            # serialize all non-native objects to strings (e.g. datetime)
            rows = []
            for row in data_head:
                row_str = []
                for cell in row:
                    if isinstance(cell, str) or cell is None:
                        row_str.append(cell)
                    else:
                        row_str.append(str(cell))
                rows.append(row_str)
            column_names = list(result_head.keys())
            sources[table.table_link]["tables"].append(
                {
                    "name": table_name,
                    "description": str(table.table_description),
                    "columns": column_names,
                    "rows": rows,
                }
            )
    return JSONResponse(status_code=200, content=sources)


class ImportSourcesRequest(BaseModel):
    token: str
    key_name: str
    links: List[str]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "user_token",
                    "key_name": "source_key",
                    "links": [
                        "https://example.com/source1",
                        "https://example.com/source2",
                    ],
                }
            ]
        }
    }


@router.post("/sources/import")
async def sources_import_route(req: ImportSourcesRequest):
    """
    Import sources into the OracleSources table in the internal database.
    """
    ts, timings = time.time(), []
    if not (await validate_user(req.token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    if not req.links:
        return
    api_key = get_api_key_from_key_name(req.key_name)
    sources_to_parse = []
    for link in req.links:
        source_type = get_source_type(link)
        sources_to_parse.append({"link": link, "type": source_type})
    json_data = {
        "api_key": api_key,
        "sources": sources_to_parse,
        "resummarize": True,
    }
    LOGGER.debug(f"Parsing sources: {sources_to_parse}")
    # each source now contains "text" and "summary" keys
    sources_parsed = await make_request(
        DEFOG_BASE_URL + "/unstructured_data/parse", json_data
    )
    sources_to_insert = []
    for source in sources_parsed:
        attributes = source.get("attributes")
        if isinstance(attributes, Dict) or isinstance(attributes, List):
            attributes = json.dumps(attributes)
        source_to_insert = {
            "api_key": api_key,
            "link": source["link"],
            "title": source.get("title", ""),
            "position": source.get("position"),
            "source_type": source.get("type"),
            "attributes": attributes,
            "snippet": source.get("snippet"),
            "text_parsed": source.get("text"),
            "text_summary": source.get("summary"),
        }
        sources_to_insert.append(source_to_insert)
    with Session(engine) as session:
        # insert the sources into the database if not present. otherwise update
        for source in sources_to_insert:
            stmt = select(OracleSources).where(
                OracleSources.api_key == api_key, OracleSources.link == source["link"]
            )
            result = session.execute(stmt)
            if result.scalar() is None:
                stmt = insert(OracleSources).values(source)
                session.execute(stmt)
                LOGGER.debug(f"Inserted source {source['link']} into the database.")
            else:
                stmt = (
                    update(OracleSources)
                    .where(
                        OracleSources.api_key == api_key,
                        OracleSources.link == source["link"],
                    )
                    .values(source)
                )
                session.execute(stmt)
                LOGGER.debug(f"Updated source {source['link']} in the database.")
        session.commit()
    LOGGER.debug(f"Inserted {len(sources_to_insert)} sources into the database.")
    ts = save_timing(ts, "Sources parsed", timings)

    parse_table_tasks = []
    table_keys = []
    for source in sources_parsed:
        for i, table in enumerate(source.get("tables", [])):
            column_names = table.get("column_names")
            rows = table.get("rows")
            if not column_names or not rows:
                LOGGER.error(
                    f"No column names or rows found in table {i}. Skipping table:\n{table}"
                )
                continue
            table_data = {
                "api_key": api_key,
                "all_rows": [table["column_names"]] + table["rows"],
                "previous_text": table.get("previous_text"),
            }
            if table.get("table_page", None):
                table_keys.append(
                    (source["link"], table["table_page"])
                )  # use table page as index if available
            else:
                table_keys.append((source["link"], i))
            parse_table_tasks.append(
                make_request(
                    DEFOG_BASE_URL + "/unstructured_data/infer_table_properties",
                    table_data,
                )
            )
    parsed_tables = await asyncio.gather(*parse_table_tasks)
    ts = save_timing(ts, "Tables parsed", timings)

    inserted_tables = {}
    for (link, table_index), parsed_table in zip(table_keys, parsed_tables):
        try:
            # input validation
            if "table_name" not in parsed_table:
                LOGGER.error("No table name found in parsed table.")
                continue
            table_name = parsed_table["table_name"]
            table_description = parsed_table.get("table_description", None)
            if "columns" not in parsed_table:
                LOGGER.error(f"No columns found in parsed table `{table_name}`.")
                continue
            columns = parsed_table["columns"]
            column_names = [column["column_name"] for column in columns]
            num_cols = len(column_names)
            if "rows" not in parsed_table:
                LOGGER.error(f"No rows found in parsed table `{table_name}`.")
                continue
            rows = parsed_table["rows"]  # 2D list of data
            # check data has correct number of columns passed for each row
            if not all(len(row) == num_cols for row in rows):
                LOGGER.error(
                    f"Unable to insert table `{table_name}.` Data has mismatched number of columns for each row. Header has {len(data[0])} columns: {data[0]}, but data has {len(data[1])} columns: {data[1]}."
                )
                continue

            schema_table_name = f"{IMPORTED_SCHEMA}.{table_name}"
            # create the table and insert the data into imported_tables database, parsed schema
            data = [column_names] + rows
            success, old_table_name = update_imported_tables_db(
                api_key, link, table_index, table_name, data, IMPORTED_SCHEMA
            )
            if not success:
                LOGGER.error(
                    f"Failed to update imported tables database for table `{table_name}`."
                )
                continue
            # update the imported_tables table in internal db
            update_imported_tables(
                api_key,
                link,
                table_index,
                old_table_name,
                schema_table_name,
                table_description,
            )
            [
                column.pop("fn", None) for column in columns
            ]  # remove "fn" key if present before updating metadata
            inserted_tables[schema_table_name] = columns
        except Exception as e:
            LOGGER.error(
                f"Error occurred in parsing table: {e}\n{traceback.format_exc()}"
            )
    ts = save_timing(ts, "Tables saved", timings)
    # get and update metadata if inserted_tables is not empty
    if inserted_tables:
        response = await make_request(
            DEFOG_BASE_URL + "/get_metadata", {"api_key": api_key, "imported": True}
        )
        md = response.get("table_metadata", {}) if response else {}
        md.update(inserted_tables)
        response = await make_request(
            DEFOG_BASE_URL + "/update_metadata",
            {
                "api_key": api_key,
                "table_metadata": md,
                "db_type": INTERNAL_DB,
                "imported": True,
            },
        )
        LOGGER.info(f"Updated metadata for api_key {api_key}")
        save_and_log(ts, "Metadata updated", timings)
    else:
        LOGGER.info("No parsed tables to save.")
    return JSONResponse(
        status_code=200,
        content={
            "message": "Sources imported successfully",
        },
    )


class DeleteSourceRequest(BaseModel):
    token: str
    key_name: str
    link: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "user_token",
                    "key_name": "source_key",
                    "link": "https://example.com/source1",
                }
            ]
        }
    }


@router.post("/sources/delete")
async def delete_source(req: DeleteSourceRequest):
    """
    Delete a source from the OracleSources table in the internal database.
    """
    if not (await validate_user(req.token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(req.key_name)
    # delete source from oracle_sources
    with Session(engine) as session:
        stmt = select(OracleSources).where(
            OracleSources.api_key == api_key, OracleSources.link == req.link
        )
        result = session.execute(stmt)
        source = result.fetchone()
        if source is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Not Found",
                    "message": "Source not found",
                },
            )
        stmt = delete(OracleSources).where(
            OracleSources.api_key == api_key, OracleSources.link == req.link
        )
        session.execute(stmt)
        session.commit()
    # delete source's tables from imported_tables
    with imported_tables_engine.begin() as imported_tables_connection:
        # get table_name for all entries with the link
        stmt = select(ImportedTables.table_name).where(
            ImportedTables.table_link == req.link
        )
        result = imported_tables_connection.execute(stmt)
        tables = result.fetchall()
        for table in tables:
            table_name = table.table_name
            # drop table from imported_tables database
            table = text(f"DROP TABLE IF EXISTS {table_name}")
            imported_tables_connection.execute(table)
            LOGGER.info(f"Dropped table `{table_name}` from {IMPORTED_SCHEMA} schema.")
        # delete all entries with the link
        stmt = delete(ImportedTables).where(ImportedTables.table_link == req.link)
        imported_tables_connection.execute(stmt)
        LOGGER.info(f"Deleted all entries with link=`{req.link}` from imported_tables.")
    return JSONResponse(
        status_code=200,
        content={
            "message": "Source deleted successfully",
        },
    )


class CreateImportedTablesRequest(BaseModel):
    token: str
    key_name: str
    data: List[List[str]]
    link: str
    table_index: int
    table_name: str
    table_description: str = ""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "user_token",
                    "key_name": "source_key",
                    "data": [["column1", "column2"], ["value1", "value2"]],
                    "link": "https://example.com/source1",
                    "table_index": 0,
                    "table_name": "example_table",
                    "table_description": "Example table description",
                }
            ]
        }
    }


@router.post("/imported_tables/create")
async def imported_tables_create_route(req: CreateImportedTablesRequest):
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
        "token": "...",
        "key_name": "...",
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
    if not (await validate_user(req.token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(req.key_name)
    success, old_table_name = update_imported_tables_db(
        api_key=api_key,
        link=req.link,
        table_index=req.table_index,
        new_table_name=req.table_name,
        data=req.data,
        schema_name=IMPORTED_SCHEMA,
    )
    if not success:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to update imported tables database",
            },
        )
    LOGGER.debug(f"Updated imported tables database with table: {req.table_name}")
    LOGGER.debug(f"Old table name: {old_table_name}")

    success = update_imported_tables(
        api_key=api_key,
        link=req.link,
        table_index=req.table_index,
        old_table_name=old_table_name,
        table_name=req.table_name,
        table_description=req.table_description,
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
        "all_rows": req.data,
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
        LOGGER.error(
            f"No columns or table name in table properties: {table_properties}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "Failed to infer table properties",
            },
        )
    if len(table_properties["columns"]) != len(req.data[0]):
        LOGGER.error(
            f"Number of columns in table properties does not match data: {table_properties}"
        )
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
            "db_type": INTERNAL_DB,
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
            "table_name": req.table_name,
        },
    )
