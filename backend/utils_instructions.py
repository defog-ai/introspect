########################################
### Instructions Related Functions Below ###
########################################

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import Instructions
from db_config import engine


async def get_instructions(db_name: str) -> str:
    """
    Get instructions for a given API key.
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
    Update or insert instructions for a given API key.
    Args:
        db_name: The API key to update metadata for
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
