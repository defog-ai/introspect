import logging
import os
import time
from typing import Any, Dict
import uuid

import pandas as pd
from sqlalchemy import text

from db_utils import get_db_type_creds
from db_config import INTERNAL_DB, imported_tables_engine, temp_tables_engine
from generic_utils import make_request
from utils_imported_data import IMPORTED_SCHEMA
from utils_logging import log_timings, save_and_log, save_timing
from utils_sql import execute_sql, add_schema_to_tables

LOGGER = logging.getLogger(__name__)
DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


async def xdb_query(
    api_key: str, question: str, return_debug: bool = False
) -> Dict[str, Any]:
    """
    Given the original api_key and question, attempts to get an answer using
    data from both main/imported databases.
    1. gets pair of queries for main and imported database
    2. runs queries where required
    3. stores results into a temp DB
    4. creates adhoc metadata for the temp DB
    5. gqc with the temp DB's metadata
    6. runs query
    7. tears down by removing temp tables
    """
    ts, timings = time.time(), []
    # 1. get source queries from defog
    try:
        source_queries = await make_request(
            f"{DEFOG_BASE_URL}/xdb/get_source_queries",
            {"api_key": api_key, "question": question},
        )
    except Exception as e:
        LOGGER.error(f"Failed to get source queries:\n{str(e)}")
        return {"error": "Failed to get source queries"}
    ts = save_timing(ts, "get source queries", timings)

    # 2. run queries on main and imported databases and fetch data
    if "main" in source_queries:
        main_sql = source_queries["main"]
        db_type, db_creds = await get_db_type_creds(api_key)
        data_main, err_msg = await execute_sql(db_type, db_creds, main_sql)
        if err_msg:
            LOGGER.error(
                f"Error occurred in running SQL for main database: {err_msg}\nSQL: {main_sql}"
            )
            import traceback

            LOGGER.error(traceback.format_exc())
            return {
                "error": f"Error occurred in running SQL for main database: {err_msg}\nSQL: {main_sql}"
            }
        LOGGER.debug(f"Data from main database: {data_main.head()}")
        ts = save_timing(ts, "get main data", timings)
    else:
        data_main = None
    if "imported" in source_queries:
        imported_sql = source_queries["imported"]
        # needed in case "imported" schema wasn't added during metadata generation
        imported_sql = add_schema_to_tables(imported_sql, IMPORTED_SCHEMA)
        try:
            data_imported = pd.read_sql(imported_sql, imported_tables_engine)
        except Exception as e:
            LOGGER.error(
                f"Error occurred in running SQL for imported database: {e}\nSQL: {imported_sql}"
            )
            return {
                "error": f"Error occurred in running SQL for imported database: {e}\nSQL: {imported_sql}"
            }
        LOGGER.debug(f"Data from imported database: {data_imported.head()}")
        ts = save_timing(ts, "get imported data", timings)
    else:
        data_imported = None
    # return early if combination is not required
    if "combined" not in source_queries:
        log_timings(timings)
        if "main" in source_queries:
            return {
                "data": data_main.values.tolist(),
                "columns": data_main.columns.tolist(),
                "sql": {"main": source_queries["main"]},
            }
        elif "imported" in source_queries:
            return {
                "data": data_imported.values.tolist(),
                "columns": data_imported.columns.tolist(),
                "sql": {"imported": source_queries["imported"]},
            }
        else:
            return {"error": "No data available to answer the question."}

    # 3. store data into a temporary table in the internal database
    uuid = generate_uuid()
    request_suffix = f"{api_key}_{uuid}"
    table_names_full = [f"main_{request_suffix}", f"imported_{request_suffix}"]
    # remove existing temp tables starting with the same prefix
    with temp_tables_engine.begin() as conn:
        # select all tables starting with the prefix
        stmt = f"SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%_{request_suffix}'"
        result = conn.execute(text(stmt))
        tables = result.fetchall()
        for table in tables:
            # drop the table
            conn.execute(f"DROP TABLE {table[0]}")
            LOGGER.info(f"Dropped table before starting xdb request: {table[0]}")
    # store data into temp tables
    try:
        data_main.to_sql(
            f"main_{request_suffix}",
            temp_tables_engine,
            if_exists="replace",
            index=False,
        )
    except Exception as e:
        LOGGER.error(f"Error occurred in storing data_main into temp table: {e}")
        return {"error": f"Error occurred in storing data_main into temp table: {e}"}
    try:
        data_imported.to_sql(
            f"imported_{request_suffix}",
            temp_tables_engine,
            if_exists="replace",
            index=False,
        )
    except Exception as e:
        LOGGER.error(f"Error occurred in storing data_imported into temp table: {e}")
        return {
            "error": f"Error occurred in storing data_imported into temp table: {e}"
        }
    ts = save_timing(ts, "store data into temp tables", timings)

    # 4. get metadata for the temp DB where table_name begins with the prefix
    md_both = {}
    for table in table_names_full:
        get_md_query = f"SELECT CAST(column_name AS TEXT), CAST(data_type AS TEXT) FROM information_schema.columns WHERE table_name::text = '{table}'"
        with temp_tables_engine.begin() as conn:
            try:
                result = conn.execute(text(get_md_query))
                rows = result.fetchall()
            except Exception as e:
                LOGGER.error(f"Failed to get metadata for {table} data: {e}")
                return {"error": f"Failed to get metadata for {table} data: {e}"}
        if not rows:
            LOGGER.error(f"Failed to get metadata for {table} data")
            return {"error": f"Failed to get metadata for {table} data"}
        columns = [{"column_name": i[0], "data_type": i[1]} for i in rows]
        LOGGER.debug(f"Metadata for {table} data: {columns}")
        md_both[f"{table}"] = columns
    ts = save_timing(ts, "get metadata for temp tables", timings)

    # 5. gqc with the temp DB's metadata
    gqc_request = {
        "api_key": api_key,
        "question": source_queries["combined"],
        "metadata": md_both,
        "db_type": INTERNAL_DB,
    }
    try:
        gqc_response = await make_request(
            f"{DEFOG_BASE_URL}/generate_query_chat", gqc_request
        )
    except Exception as e:
        LOGGER.error(f"Failed to generate final query: {e}")
        return {"error": f"Failed to generate final query: {e}"}
    if "error" in gqc_response and gqc_response["error"]:
        LOGGER.error(f"Error in generating final query: {gqc_response['error']}")
        return {"error": f"Error in generating final query: {gqc_response['error']}"}
    ts = save_timing(ts, "generate final query", timings)

    # 6. run query
    final_sql = gqc_response["sql"]
    try:
        final_data = pd.read_sql(final_sql, temp_tables_engine)
    except Exception as e:
        LOGGER.error(f"Error occurred in running final SQL: {e}\nSQL: {final_sql}")
        return {"error": f"Error occurred in running final SQL: {e}\nSQL: {final_sql}"}
    LOGGER.debug(f"Final data: {final_data.head()}")
    ts = save_timing(ts, "get final data", timings)

    # 7. tear down
    with temp_tables_engine.begin() as conn:
        for table in table_names_full:
            conn.execute(text(f"DROP TABLE {table}"))
            LOGGER.info(f"Dropped temp table after xdb request: {table}")
    save_and_log(ts, "dropped temp tables", timings)
    result = {
        "data": final_data.values.tolist(),
        "columns": final_data.columns.tolist(),
        "sql": final_sql,
    }
    if return_debug:
        result["debug"] = {
            "main": {
                "sql": source_queries.get("main"),
                "data": data_main.values.tolist(),
                "columns": data_main.columns.tolist(),
            },
            "imported": {
                "sql": source_queries.get("imported"),
                "data": data_imported.values.tolist(),
                "columns": data_imported.columns.tolist(),
            },
        }
    return result


def generate_uuid():
    return str(uuid.uuid4()).replace("-", "")[:4]
