from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import OracleReports
from db_config import engine
import asyncio
from auth_utils import validate_user
import json

router = APIRouter(tags=["Oracle"],)

async def oracle_thinking_stream(report_id: int):
    """
    Asynchronous generator that yields events until the report is done
    """
    current_thinking_steps = []
    async with AsyncSession(engine) as session:
        async with session.begin():
            while True:
                report = await session.get(OracleReports, report_id)
                if report.status == "DONE":
                    break

                if current_thinking_steps != report.thinking_steps:
                    # get all the thinking steps that are not in current thinking steps
                    new_thinking_steps = [step for step in report.thinking_steps if step not in current_thinking_steps]
                    yield f"data: {json.dumps(new_thinking_steps)}\n\n"
                    current_thinking_steps = report.thinking_steps
                await asyncio.sleep(1)
    yield "data: Stream closed\n\n"

# return a stream for updating the report's thinking status
@router.get("/oracle/update_report_thinking_status")
async def update_report_thinking_status(report_id: int, x_auth_token: str = Header(None)):
    if not (await validate_user(x_auth_token)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return StreamingResponse(oracle_thinking_stream(report_id), media_type="text/event-stream")