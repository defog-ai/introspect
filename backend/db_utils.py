"""Database credential utility functions."""

from typing import Dict, Tuple
from defog.query import async_execute_query_once
from sqlalchemy import delete, select, update, insert
from utils_md import get_metadata
from db_config import engine
from db_models import DbCreds
from utils_logging import LOGGER
from defog import Defog
import os
import asyncio
import json

home_dir = os.path.expanduser("~")
defog_path = os.path.join(home_dir, ".defog")


async def get_db_type_creds(db_name: str) -> Tuple[str, Dict[str, str]] | None:
    async with engine.begin() as conn:
        row = await conn.execute(
            select(DbCreds.db_type, DbCreds.db_creds).where(DbCreds.db_name == db_name)
        )
        row = row.fetchone()
    return row


async def get_db_names() -> list[str]:
    async with engine.begin() as conn:
        result = await conn.execute(select(DbCreds.db_name))
        db_names = result.scalars().all()
    return db_names


async def update_db_type_creds(db_name, db_type, db_creds):
    async with engine.begin() as conn:
        # first, check if the record exists
        record = await conn.execute(select(DbCreds).where(DbCreds.db_name == db_name))

        record = record.fetchone()

        if record:
            await conn.execute(
                update(DbCreds)
                .where(DbCreds.db_name == db_name)
                .values(db_type=db_type, db_creds=db_creds)
            )
        else:
            await conn.execute(
                insert(DbCreds).values(
                    db_name=db_name, db_type=db_type, db_creds=db_creds
                )
            )

    return True


async def validate_db_connection(db_type, db_creds):
    for k in ["api_key", "db_type"]:
        if isinstance(db_creds, dict) and k in db_creds:
            del db_creds[k]

    if db_type == "bigquery":
        db_creds["json_key_path"] = "./bq.json"

    sql_query = "SELECT 'test';"
    try:
        await async_execute_query_once(
            db_type,
            db_creds,
            sql_query,
        )
        return True
    except Exception as e:
        LOGGER.error(str(e))
        return False


async def get_db_info(db_name):
    res = await get_db_type_creds(db_name)
    if not res:
        raise Exception("No db creds found")

    db_type, db_creds = res
    defog = Defog(api_key=db_name, db_type=db_type, db_creds=db_creds)
    can_connect = await validate_db_connection(db_type, db_creds)
    table_names = []

    if can_connect:
        table_names = await asyncio.to_thread(
            defog.generate_db_schema,
            tables=[],
            upload=False,
            scan=False,
            return_tables_only=True,
        )

    db_type = defog.db_type
    db_creds = defog.db_creds

    # get selected_tables from file. this is a legacy way of keeping track
    # of tables that the user has selected to add to the metadata
    # ideally we'd want this to be stored somewhere more persistent like in
    # the database, but we just keep it around for now to avoid breaking changes
    selected_tables_path = os.path.join(defog_path, f"selected_tables_{db_name}.json")
    if os.path.exists(selected_tables_path):
        with open(selected_tables_path, "r") as f:
            selected_tables_saved = json.load(f)
            if isinstance(selected_tables_saved, list):
                selected_tables = selected_tables_saved
            else:
                selected_tables = table_names
    else:
        selected_tables = table_names

    metadata = await get_metadata(db_name)

    return {
        "db_name": db_name,
        "tables": table_names,
        "db_creds": db_creds,
        "db_type": db_type,
        "selected_tables": selected_tables,
        "can_connect": can_connect,
        "metadata": metadata,
    }


async def delete_db_info(db_name):
    async with engine.begin() as conn:
        await conn.execute(delete(DbCreds).where(DbCreds.db_name == db_name))
