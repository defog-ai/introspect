"""Database credential utility functions."""
from typing import Dict, Tuple
from sqlalchemy import select, update, insert
from db_config import engine
from db_models import DbCreds
from utils_logging import LOGGER

async def get_db_type_creds(api_key: str) -> Tuple[str, Dict[str, str]]:
    async with engine.begin() as conn:
        row = await conn.execute(
            select(DbCreds.db_type, DbCreds.db_creds).where(DbCreds.api_key == api_key)
        )
        row = row.fetchone()
    return row


async def update_db_type_creds(api_key, db_type, db_creds):
    async with engine.begin() as conn:
        # first, check if the record exists
        record = await conn.execute(select(DbCreds).where(DbCreds.api_key == api_key))

        record = record.fetchone()

        if record:
            await conn.execute(
                update(DbCreds)
                .where(DbCreds.api_key == api_key)
                .values(db_type=db_type, db_creds=db_creds)
            )
        else:
            await conn.execute(
                insert(DbCreds).values(
                    api_key=api_key, db_type=db_type, db_creds=db_creds
                )
            )

    return True
