"""Database credential utility functions."""

from typing import Dict, Tuple
from defog.query import async_execute_query_once
from sqlalchemy import select, update, insert
from db_config import engine
from db_models import DbCreds
from utils_logging import LOGGER


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
