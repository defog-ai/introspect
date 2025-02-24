########################################
### Instructions Related Functions Below ###
########################################

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import Instructions
from db_config import engine
from utils_logging import LOGGER


async def get_instructions(db_name: str) -> str:
    """
    Get instructions for a given db_name.
    Returns a list of dictionaries, each containing:
        - table_name: str
        - column_name: str
        - data_type: str
        - column_description: str
    """
    async with AsyncSession(engine) as session:
        async with session.begin():
            result = await session.execute(
                select(
                    Instructions.sql_instructions,
                ).where(Instructions.db_name == db_name)
            )
            instructions_result = result.scalar_one_or_none()
            if not instructions_result:
                return ""
            else:
                return instructions_result


async def set_instructions(db_name: str, instructions_text: str):
    """
    Update or insert instructions for a given db_name.
    Args:
        db_name: The db_name to update metadata for
        instructions_text: The instructions to set
    """
    if not instructions_text:
        return
    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = select(Instructions).where(
                Instructions.db_name == db_name
            )
            result = await session.execute(stmt)
            instruction_record = result.scalar_one_or_none()
            if instruction_record:
                await session.execute(
                    update(Instructions).values(
                        sql_instructions=instructions_text
                    ).where(Instructions.db_name == db_name)
                )
            else:
                await session.execute(
                    insert(Instructions).values(
                        db_name=db_name, sql_instructions=instructions_text
                    )
                )
    return


async def get_join_hints(db_name: str) -> list[list[str]] | None:
    """
    Get join hints for a given db_name.
    """
    async with engine.begin() as connection:
        result = await connection.execute(
            select(Instructions.join_hints).where(Instructions.db_name == db_name)
        )
        return result.scalar_one_or_none()


async def delete_join_hints(db_name: str):
    """
    Delete join hints for a given db_name.
    """
    async with AsyncSession(engine) as session:
        async with session.begin():
            await session.execute(
                delete(Instructions).where(Instructions.db_name == db_name)
            )
    return


async def set_join_hints(db_name: str, join_hints: list[list[str]]):
    """
    Set join hints for a given db_name.
    """
    async with AsyncSession(engine) as session:
        async with session.begin():
            # check if db_name has a row in instructions table
            result = await session.execute(
                select(Instructions).where(Instructions.db_name == db_name)
            )
            instruction_record = result.scalar_one_or_none()
            if instruction_record:
                await session.execute(
                    update(Instructions).values(join_hints=join_hints).where(Instructions.db_name == db_name)
                )
            else:
                await session.execute(
                    insert(Instructions).values(db_name=db_name, join_hints=join_hints)
                )
    return
