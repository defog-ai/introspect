import os
import traceback

from db_config import engine
from db_models import TableInfo
from defog.llm.utils import chat_async
from llm_api import O3_MINI
from pydantic import BaseModel
from request_models import TableDescription
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from utils_logging import LOGGER
from utils_md import mk_create_ddl

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BACKEND_DIR, "prompts/table_descriptions/system.md"), "r") as f:
    TABLE_DESCRIPTIONS_SYSTEM_PROMPT = f.read()
with open(os.path.join(BACKEND_DIR, "prompts/table_descriptions/user.md"), "r") as f:
    TABLE_DESCRIPTIONS_USER_PROMPT = f.read()


### CRUD operations for table descriptions ###


async def get_all_table_descriptions(db_name: str) -> list[TableDescription]:
    """
    Get all table descriptions for a given database.

    Args:
        db_name: The name of the database
        session: SQLAlchemy session

    Returns:
        List of TableDescription objects.
    """
    try:
        async with engine.begin() as conn:
            table_infos = await conn.execute(
                select(TableInfo.table_name, TableInfo.table_description).where(
                    TableInfo.db_name == db_name
                )
            )
            return [
                TableDescription(
                    table_name=table_info[0],
                    table_description=table_info[1],
                )
                for table_info in table_infos.fetchall()
            ]
    except Exception as e:
        LOGGER.error(f"Error getting table descriptions: {str(e)}")
        LOGGER.error(traceback.format_exc())
        return []


async def update_table_descriptions(
    db_name: str,
    table_descriptions: list[TableDescription],
) -> None:
    """
    Update table descriptions for a given database.
    Creates new entries if they don't exist, updates existing ones.

    Args:
        db_name: The name of the database
        table_descriptions: TableDescriptions object
    """
    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                for table_description in table_descriptions:
                    table_name = table_description.table_name
                    description = table_description.table_description
                    # Try to find existing entry
                    table_info = await session.execute(
                        select(TableInfo).where(
                            TableInfo.db_name == db_name,
                            TableInfo.table_name == table_name,
                        )
                    )
                    table_info = table_info.scalar_one_or_none()
                    if table_info:
                        # Update existing
                        table_info.table_description = description
                    else:
                        # Create new
                        new_table_info = TableInfo(
                            db_name=db_name,
                            table_name=table_name,
                            table_description=description,
                        )
                        session.add(new_table_info)
    except Exception as e:
        LOGGER.error(f"Error updating table descriptions: {str(e)}")


async def delete_table_descriptions(db_name: str, table_names: list[str] = []) -> None:
    """
    Delete table descriptions for a given database.
    If no table names are provided, all table descriptions for the specified
    database will be deleted.
    """
    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                if not table_names:
                    await session.execute(
                        delete(TableInfo).where(TableInfo.db_name == db_name)
                    )
                else:
                    for table_name in table_names:
                        await session.execute(
                            delete(TableInfo).where(
                                TableInfo.db_name == db_name,
                                TableInfo.table_name == table_name,
                            )
                        )
    except Exception as e:
        LOGGER.error(f"Error deleting table descriptions: {str(e)}")


### LLM inference for table descriptions ###


class TableDescriptions(BaseModel):
    table_descriptions: list[TableDescription]


async def infer_table_descriptions(
    db_name: str, metadata: list[dict[str, str]]
) -> list[TableDescription]:
    """
    Infer table descriptions for a given database's metadata using an LLM.
    Note that this doesn't actually update the table descriptions in the database,
    so as to separate the concerns of generating the descriptions from the
    updating of the table descriptions more cleanly.

    Args:
        db_name: The name of the database
        metadata: List of dictionaries, where each dictionary maps to a column's
            name, data type, description, and table name. We assume the list to
            be ordered by table name. If you are using `get_metadata` to get
            the metadata, it already satisfies this condition.

    Returns:
        TableDescriptions object
    """
    if not metadata:
        LOGGER.warning("No metadata provided, returning empty table descriptions")
        return []
    metadata_str = mk_create_ddl(metadata)
    user_prompt = TABLE_DESCRIPTIONS_USER_PROMPT.format(
        db_name=db_name, metadata_str=metadata_str
    )
    messages = [
        {"role": "system", "content": TABLE_DESCRIPTIONS_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    response = await chat_async(
        model=O3_MINI,
        messages=messages,
        response_format=TableDescriptions,
    )
    LOGGER.info(f"Table descriptions generation took {response.time:.2f}s")
    return response.content.table_descriptions
