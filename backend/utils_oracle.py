from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from oracle_models import Clarification
from db_models import OracleGuidelines
from db_config import engine
from utils_md import get_metadata, mk_create_ddl
from oracle.constants import TaskType
from defog.llm.utils import chat_async
from llm_api import O3_MINI
from utils_logging import LOGGER

# read in prompts
with open("./prompts/oracle/clarification/sys.txt", "r") as f:
    ORACLE_CLARIFICATION_EXPLORATION_SYS_PROMPT = f.read()
with open("./prompts/oracle/clarification/user.txt", "r") as f:
    ORACLE_CLARIFICATION_EXPLORATION_USER_PROMPT = f.read()

CLARIFICATION_SYS_PROMPTS = {
    TaskType.EXPLORATION: ORACLE_CLARIFICATION_EXPLORATION_SYS_PROMPT,
}
CLARIFICATION_USER_PROMPTS = {
    TaskType.EXPLORATION: ORACLE_CLARIFICATION_EXPLORATION_USER_PROMPT,
}


from pydantic import BaseModel


class ClarificationOutput(BaseModel):
    clarifications: list[Clarification]


async def clarify_question(
    user_question: str,
    db_name: str,
    oracle_guidelines: str,
    max_clarifications: int = 5,
    task_type: TaskType = TaskType.EXPLORATION,
) -> dict:
    metadata = await get_metadata(db_name)
    ddl = mk_create_ddl(metadata)

    user_prompt = CLARIFICATION_USER_PROMPTS[task_type].format(
        question=user_question,
        metadata=ddl,
        context=oracle_guidelines,
        max_clarifications=max_clarifications,
    )

    messages = [
        {"role": "system", "content": CLARIFICATION_SYS_PROMPTS[task_type]},
        {"role": "user", "content": user_prompt},
    ]

    response = await chat_async(
        messages=messages,
        model=O3_MINI,
        response_format=ClarificationOutput,
    )

    clarification_output: ClarificationOutput = response.content

    return clarification_output.model_dump()


async def set_oracle_guidelines(db_name: str, guidelines: str) -> str:
    # save to oracle_guidelines table, overwriting if already exists
    async with AsyncSession(engine) as session:
        async with session.begin():
            # check if the db_name already exists
            result = await session.execute(
                select(OracleGuidelines).where(OracleGuidelines.db_name == db_name)
            )
            if result.scalar_one_or_none():
                await session.execute(
                    update(OracleGuidelines).values(
                        db_name=db_name,
                        clarification_guidelines=guidelines,
                    )
                )
            else:
                await session.execute(
                    insert(OracleGuidelines).values(
                        db_name=db_name,
                        clarification_guidelines=guidelines,
                    )
                )
            LOGGER.debug(f"Saved clarification guidelines to DB for API key {db_name}")


async def get_oracle_guidelines(db_name: str) -> str:
    guidelines = None
    async with AsyncSession(engine) as session:
        async with session.begin():
            result = await session.execute(
                select(OracleGuidelines.clarification_guidelines).where(
                    OracleGuidelines.db_name == db_name
                )
            )
            guidelines = result.scalar_one_or_none()

    return guidelines
