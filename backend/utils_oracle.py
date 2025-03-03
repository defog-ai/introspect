from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from oracle_models import Clarification
from db_models import OracleGuidelines, OracleReports, PDFFiles
from db_config import engine
from utils_md import get_metadata, mk_create_ddl
from defog.llm.utils import chat_async
from utils_logging import LOGGER
from typing import Literal, Any
from datetime import datetime
from sqlalchemy.orm.attributes import flag_modified


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
        model="gpt-4o",
        response_format=ClarificationOutput,
    )

    clarification_output = response.content.model_dump()
    clarification_output["clarifications"].append(
        {
            "clarification": "Any other context you would like to give us?",
            "input_type": "text",
            "options": [],
        }
    )

    return clarification_output


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

async def set_oracle_report(
    report_id: str = None,
    db_name: str = None,
    report_name: str = None,
    inputs: dict = None,
    mdx: str = None,
    analyses: list = None,
    thinking_steps: list = None,
    status: Literal["INITIALIZED", "THINKING", "ERRORED", "DONE"] = None,
    pdf_file_ids: list[int] = [],
) -> str:
    async with AsyncSession(engine) as session:
        async with session.begin():
            if not report_id:    
                report_id = await session.execute(
                    insert(OracleReports).values(
                        db_name=db_name,
                        report_name=report_name,
                        created_ts=datetime.now(),
                        inputs=inputs,
                        mdx=mdx,
                        analyses=analyses,
                        status=status,
                        pdf_file_ids=pdf_file_ids,
                    ).returning(OracleReports.report_id)
                )
                report_id = report_id.scalar_one()
            else:
                # first, get the report
                report = await session.execute(
                    select(OracleReports).where(
                        OracleReports.report_id == report_id
                    )
                )
                report = report.scalar_one_or_none()
                if not report:
                    return None
                
                if report_name:
                    report.report_name = report_name
                if db_name:
                    report.db_name = db_name
                if inputs:
                    report.inputs = inputs
                    flag_modified(report, "inputs")
                if mdx:
                    report.mdx = mdx
                if analyses:
                    report.analyses = analyses
                    flag_modified(report, "analyses")
                if thinking_steps:
                    report.thinking_steps = thinking_steps
                    flag_modified(report, "thinking_steps")
                if status:
                    report.status = status
                if pdf_file_ids and len(pdf_file_ids) > 0:
                    report.pdf_file_ids = pdf_file_ids

    return report_id

async def append_thinking_step_to_oracle_report(report_id: int, thinking_step: Any):
    async with AsyncSession(engine) as session:
        async with session.begin():
            report = await session.execute(
                select(OracleReports).where(
                    OracleReports.report_id == report_id
                )
            )
            report = report.scalar_one_or_none()
            if not report:
                return None
            
            thinking_steps = report.thinking_steps
            if thinking_steps is None:
                thinking_steps = []
            thinking_steps.append(thinking_step)
            report.thinking_steps = thinking_steps
            flag_modified(report, "thinking_steps")
    
    return

async def post_tool_call_func(function_name, input_args, tool_result, report_id):
    print("calling post_tool_call_func", flush=True)
    print(f"current report id: {report_id}", flush=True)
    
    thinking_step_inputs = input_args
    thinking_step_result = tool_result

    # check if thinking_step_result is a pydantic model. if so, convert to dict
    if isinstance(thinking_step_result, BaseModel):
        thinking_step_result = thinking_step_result.model_dump()

    await append_thinking_step_to_oracle_report(
        report_id=report_id, 
        thinking_step = {
            "function_name": function_name,
            "inputs": thinking_step_inputs,
            "result": thinking_step_result
        }
    )

async def upload_pdf_files(pdf_files: list) -> list[int]:
    pdf_file_ids = []
    async with AsyncSession(engine) as session:
        async with session.begin():
            for pdf_file in pdf_files:
                pdf_file_id = await session.execute(
                    insert(PDFFiles).values(
                        file_name=pdf_file.file_name,
                        base64_data=pdf_file.base64_content
                    ).returning(PDFFiles.file_id)
                )
                pdf_file_id = pdf_file_id.scalar_one()
                pdf_file_ids.append(pdf_file_id)
    
    return pdf_file_ids

async def get_report_pdf_files(report_id: int) -> list[int]:
    async with AsyncSession(engine) as session:
        async with session.begin():
            pdf_file_ids = await session.execute(
                select(OracleReports.pdf_file_ids).where(
                    OracleReports.report_id == report_id
                )
        )
            pdf_file_ids = pdf_file_ids.scalar_one_or_none()
    
    if pdf_file_ids is None:
        pdf_file_ids = []
    return pdf_file_ids

async def get_pdf_content(file_id: int):
    async with AsyncSession(engine) as session:
        async with session.begin():
            pdf_file = await session.execute(
                select(PDFFiles).where(
                    PDFFiles.file_id == file_id
                )
            )
            pdf_file = pdf_file.scalar_one_or_none()
            
            # Create a detached copy of the data before the session closes
            if pdf_file:
                return {
                    "file_id": pdf_file.file_id,
                    "file_name": pdf_file.file_name,
                    "base64_data": pdf_file.base64_data,
                    "created_at": pdf_file.created_at
                }
    
    return None