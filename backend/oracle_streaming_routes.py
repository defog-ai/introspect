from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils_logging import LOGGER
from db_models import OracleReports, ReportStatus
from db_config import engine
import asyncio
from auth_utils import validate_user
import json

router = APIRouter(
    tags=["Oracle"],
)

sep = "\n\n------\n\n"


async def oracle_thinking_stream(report_id: int):
    """
    Asynchronous generator that yields events until the report is done.
    Efficiently monitors database changes in real-time with proper error handling.
    """
    current_thinking_steps = []
    try:
        while True:
            # Create a new session for each iteration to ensure fresh data
            async with AsyncSession(engine) as session:
                # Use a more targeted query with explicit column selection for efficiency
                result = await session.execute(
                    select(OracleReports.thinking_steps, OracleReports.status).where(
                        OracleReports.report_id == report_id
                    )
                )
                report_data = result.one_or_none()

                # Handle case where report doesn't exist
                if not report_data:
                    yield f"data: {json.dumps({'error': 'Report not found'})}{sep}"
                    break

                thinking_steps, status = report_data

                # Check if report is complete
                if status == ReportStatus.DONE:
                    # Send any remaining thinking steps
                    if thinking_steps and len(current_thinking_steps) != len(
                        thinking_steps
                    ):
                        # new_thinking_steps = thinking_steps[
                        #     len(current_thinking_steps) :
                        # ]
                        # yield f"data: {json.dumps(new_thinking_steps)}{sep}"
                        # send these one by one to keep within the limit
                        for step in thinking_steps[len(current_thinking_steps) :]:
                            yield f"data: {json.dumps(step)}{sep}"
                    yield f"data: Stream closed without errors{sep}"
                    break

                # Check for new thinking steps
                if thinking_steps and len(current_thinking_steps) != len(
                    thinking_steps
                ):
                    new_thinking_steps = thinking_steps[len(current_thinking_steps) :]
                    # yield f"data: {json.dumps(new_thinking_steps)}{sep}"
                    # send these one by one to keep within the limit
                    for step in new_thinking_steps:
                        yield f"data: {json.dumps(step)}{sep}"
                    current_thinking_steps = thinking_steps

            # Use a shorter sleep interval for more responsive updates
            # but not too short to avoid excessive database queries
            await asyncio.sleep(2)
    except Exception as e:
        # Handle exceptions and provide error information in the stream
        yield f"data: {json.dumps({'error': str(e)})}{sep}"
        yield f"data: Stream closed with error {sep}"


# return a stream for updating the report's thinking status
@router.get("/oracle/get_report_thinking_status")
async def get_report_thinking_status(report_id: int, x_auth_token: str = Header(None)):
    if not (await validate_user(x_auth_token)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return StreamingResponse(
        oracle_thinking_stream(report_id), media_type="text/event-stream"
    )
