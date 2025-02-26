from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from oracle_models import Clarification
from db_models import OracleGuidelines, OracleAnalyses, OracleReports
from db_config import engine
from utils_md import get_metadata, mk_create_ddl
from defog.llm.utils import chat_async
from utils_logging import LOGGER
from typing import Literal
from datetime import datetime
import re

# read in prompts
with open("./prompts/clarify_report/sys.txt", "r") as f:
    ORACLE_CLARIFICATION_EXPLORATION_SYS_PROMPT = f.read()
with open("./prompts/clarify_report/user.txt", "r") as f:
    ORACLE_CLARIFICATION_EXPLORATION_USER_PROMPT = f.read()

CLARIFICATION_SYS_PROMPTS = ORACLE_CLARIFICATION_EXPLORATION_SYS_PROMPT
CLARIFICATION_USER_PROMPTS = ORACLE_CLARIFICATION_EXPLORATION_USER_PROMPT


from pydantic import BaseModel


class ClarificationOutput(BaseModel):
    clarifications: list[Clarification]


async def clarify_question(
    user_question: str,
    db_name: str,
    oracle_guidelines: str,
    max_clarifications: int = 5,
) -> dict:
    metadata = await get_metadata(db_name)
    ddl = mk_create_ddl(metadata)

    user_prompt = CLARIFICATION_USER_PROMPTS.format(
        question=user_question,
        metadata=ddl,
        context=oracle_guidelines,
        max_clarifications=max_clarifications,
    )

    messages = [
        {"role": "system", "content": CLARIFICATION_SYS_PROMPTS},
        {"role": "user", "content": user_prompt},
    ]

    response = await chat_async(
        messages=messages,
        model="o3-mini",
        response_format=ClarificationOutput,
    )

    clarification_output: ClarificationOutput = response.content

    return clarification_output.model_dump()


async def set_oracle_guidelines(
    db_name: str,
    guideline_type: Literal["clarification", "generate_questions", "generate_questions_deeper", "generate_report"],
    guidelines: str
) -> str:
    # get the name of the relevant column in the database
    column_name = guideline_type + "_guidelines"

    # save to oracle_guidelines table, overwriting if already exists
    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = await session.execute(
                select(OracleGuidelines).where(OracleGuidelines.db_name == db_name)
            )
            result = stmt.scalar_one_or_none()

            if not result:
                # Add new row with the specified guideline
                await session.execute(
                    insert(OracleGuidelines).values(
                        db_name=db_name,
                        # this looks hacky, but is a great way to
                        # get the column name neatly into the query
                        # w/o re-writing a lot of boilerplate
                        **{column_name: guidelines},
                    )
                )
            else:
                # Update existing row
                setattr(result, column_name, guidelines)
                LOGGER.debug(f"Updated {guideline_type} guidelines for API key {db_name}")

    return True


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

async def set_analysis(analysis_id: str, db_name: str, sql: str, csv: str, mdx: str) -> str:
    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = await session.execute(
                select(OracleAnalyses).where(
                    OracleAnalyses.db_name == db_name,
                    OracleAnalyses.analysis_id == analysis_id,
                )
            )
            result = stmt.scalar_one_or_none()

            if not result:
                await session.execute(
                    insert(OracleAnalyses).values(
                        db_name=db_name,
                        analysis_id=analysis_id,
                        sql=sql,
                        csv=csv,
                        mdx=mdx,
                    )
                )
            else:
                await session.execute(
                    update(OracleAnalyses)
                    .where(
                        OracleAnalyses.db_name == db_name,
                        OracleAnalyses.analysis_id == analysis_id,
                    )
                    .values(sql=sql, mdx=mdx, csv=csv)
                )
                LOGGER.debug(f"Updated analysis ID {analysis_id} for API key {db_name}")
    return analysis_id

async def set_oracle_report(db_name: str, report_name: str, inputs: dict, mdx: str, analyses: list) -> str:
    async with AsyncSession(engine) as session:
        async with session.begin():
            await session.execute(
                insert(OracleReports).values(
                    db_name=db_name,
                    report_name=report_name,
                    created_ts=datetime.now(),
                    inputs=inputs,
                    mdx=mdx,
                    analyses=analyses,
                )
            )
    return True

def replace_sql_blocks(markdown: str, sql_to_analysis_id: dict) -> str:
    """
    Replace SQL code blocks in a markdown string with their corresponding analysis id,
    if a matching normalized SQL exists in the provided sql_to_analysis_id dictionary.
    
    Normalization steps:
    - Convert SQL to lowercase.
    - Replace newlines with spaces.
    - Collapse multiple spaces into a single space.
    
    Args:
        markdown (str): The markdown string containing SQL code blocks.
        sql_to_analysis_id (dict): A dictionary mapping normalized SQL strings to analysis ids.
        
    Returns:
        str: The markdown string with SQL code blocks replaced by their analysis id where applicable.
    """
    
    # Regex pattern to match SQL code blocks (```sql ... ```)
    pattern = re.compile(r'```sql\s*\n(.*?)\n```', re.DOTALL)
    
    def normalize_sql(sql: str) -> str:
        # Convert to lowercase, replace newlines with a space, and collapse extra whitespace.
        return ' '.join(sql.lower().replace('\n', ' ').split())
    
    def replacement(match: re.Match) -> str:
        sql_code = match.group(1)
        normalized = normalize_sql(sql_code)
        # Look up the normalized SQL in the dictionary.
        if normalized in sql_to_analysis_id:
            return sql_to_analysis_id[normalized]
        # If no matching analysis id is found, return the original SQL block unchanged.
        return match.group(0)
    
    # Substitute all SQL blocks using the replacement function.
    return pattern.sub(replacement, markdown)
