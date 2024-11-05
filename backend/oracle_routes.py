import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from db_utils import OracleReports, engine, validate_user
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from generic_utils import get_api_key_from_key_name, make_request
from oracle.constants import TaskStage, TaskType
from oracle.core import (
    begin_generation_task,
    gather_context,
    get_report_file_path,
    predict,
)
from oracle.explore import explore_data
from oracle.optimize import optimize
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import insert, select
from utils_logging import LOGGER, save_and_log, save_timing

router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


class ClarifyQuestionRequest(BaseModel):
    key_name: str
    token: str
    user_question: str
    task_type: Optional[TaskType] = None
    answered_clarifications: List[Dict[str, Any]] = []


@router.post("/oracle/clarify_question")
async def clarify_question(req: ClarifyQuestionRequest):
    """
    Given the question provided by the user, an optionally a list of answered
    clarifications, this endpoint will return a list of clarifications that still
    need to be addressed. If this is a new question, the task_type will be inferred.
    Otherwise, the task_type will be read from the request body and used to generate
    the remaining clarifications.

    The response contains the following fields:
        clarifications: list[dict[str, str]] Each clarification dictionary will contain:
            - clarification: str
            - input_type: str (one of single_choice, multiple_choice, number, text)
            - options: list[str]
        task_type: str
    """
    ts, timings = time.time(), []
    username = validate_user(req.token, user_type=None, get_username=True)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(req.key_name)
    ts = save_timing(ts, "validate_user", timings)

    if not req.task_type:
        clarify_task_type_request = {
            "api_key": api_key,
            "user_question": req.user_question,
        }
        try:
            clarify_task_type_response = await make_request(
                DEFOG_BASE_URL + "/oracle/clarify_task_type", clarify_task_type_request
            )
            task_type = clarify_task_type_response["task_type"]
        except Exception as e:
            LOGGER.error(f"Error getting task type: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "Unable to get task type",
                },
            )
    else:
        task_type = req.task_type
    LOGGER.debug(f"Task type: {task_type}")
    ts = save_timing(ts, "get_task_type", timings)
    clarify_request = {
        "api_key": api_key,
        "user_question": req.user_question,
        "task_type": task_type,
        "answered_clarifications": req.answered_clarifications,
    }
    try:
        clarify_response = await make_request(
            DEFOG_BASE_URL + "/oracle/clarify", clarify_request
        )
        for clarification in clarify_response["clarifications"]:
            if (
                "clarification" not in clarification
                or "input_type" not in clarification
                or "options" not in clarification
            ):
                raise ValueError(f"Invalid clarification response: {clarification}")
    except Exception as e:
        LOGGER.error(f"Error getting clarifications: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "Unable to generate clarifications",
            },
        )
    clarify_response["task_type"] = task_type
    save_and_log(ts, "get_clarifications", timings)
    return JSONResponse(content=clarify_response)


@router.post("/oracle/suggest_web_sources")
async def suggest_web_sources(req: Request):
    """
    Given the question / objective statement provided by the user, this endpoint
    will return a list of web sources that can be used to generate the report.
    """
    body = await req.json()
    key_name = body.pop("key_name")
    token = body.pop("token")
    username = validate_user(token, user_type=None, get_username=True)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    body["api_key"] = get_api_key_from_key_name(key_name)
    if "user_question" not in body:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "Missing 'user_question' field",
            },
        )
    response = await make_request(DEFOG_BASE_URL + "/unstructured_data/search", body)
    return JSONResponse(content=response)


class BeginGenerationRequest(BaseModel):
    key_name: str
    token: str
    user_question: str
    task_type: TaskType
    sources: List[str]
    clarifications: List[Dict[str, Any]]


@router.post("/oracle/begin_generation")
async def begin_generation(req: BeginGenerationRequest):
    """
    Given the question / objective statement provided by the user, as well as the
    full list of configuration options, this endpoint will begin the process of
    generating a report asynchronously as a celery task.
    """
    username = validate_user(req.token, user_type=None, get_username=True)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(req.key_name)
    # insert a new row into the OracleReports table and get a new report_id
    user_inputs = {
        "user_question": req.user_question,
        "sources": req.sources,
        "clarifications": req.clarifications,
    }
    with Session(engine) as session:
        stmt = (
            insert(OracleReports)
            .values(
                api_key=api_key,
                username=username,
                inputs=user_inputs,
                status="started",
                created_ts=datetime.now(),
            )
            .returning(OracleReports.report_id)
        )
        result = session.execute(stmt)
        report_id = result.scalar_one()
        session.commit()
    begin_generation_task.apply_async(
        args=[api_key, username, report_id, req.task_type, user_inputs]
    )
    return JSONResponse(content={"report_id": report_id, "status": "started"})


@router.post("/oracle/list_reports")
async def reports_list(req: Request):
    """
    Get the list of reports that have been generated by the user, including
    those in progress. Returns a list of dictionaries, each containing:
    - report_id
    - report_name
    - status
    - date_created
    - feedback
    """
    body = await req.json()
    key_name = body.pop("key_name")
    token = body.pop("token")
    username = validate_user(token, user_type=None, get_username=True)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(key_name)

    with Session(engine) as session:
        stmt = (
            select(
                OracleReports.report_id,
                OracleReports.report_name,
                OracleReports.status,
                OracleReports.created_ts,
                OracleReports.inputs,
            )
            .where(OracleReports.api_key == api_key, OracleReports.username == username)
            .order_by(OracleReports.created_ts.desc())
        )
        result = session.execute(stmt)
        reports = result.fetchall()

    reports_list = [
        {
            "report_id": report.report_id,
            "report_name": report.report_name,
            "status": report.status,
            "date_created": report.created_ts.isoformat(),  # Convert to ISO 8601 string
            "inputs": report.inputs,
        }
        for report in reports
    ]
    return JSONResponse(status_code=200, content={"reports": reports_list})


@router.post("/oracle/download_report")
async def download_report(req: Request):
    """
    Given a report_id, this endpoint will return the report pdf file to the user.
    """
    body = await req.json()
    key_name = body.pop("key_name")
    token = body.pop("token")
    username = validate_user(token, user_type=None, get_username=True)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(key_name)
    if "report_id" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": "Bad Request", "message": "Missing 'report_id' field"},
        )
    report_id = body["report_id"]
    report_path = get_report_file_path(api_key, report_id)
    return FileResponse(report_path, media_type="application/pdf", filename=report_path)


@router.post("/oracle/delete_report")
async def delete_report(req: Request):
    """
    Given a report_id, this endpoint will delete the report from the system.
    Reports in progress will have their associated background tasks cancelled.
    """
    body = await req.json()
    key_name = body.pop("key_name", "")
    token = body.pop("token", "")
    report_id = body.pop("report_id", None)
    username = validate_user(token, user_type=None, get_username=True)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(key_name)

    with Session(engine) as session:
        stmt = select(OracleReports).where(
            OracleReports.api_key == api_key,
            OracleReports.username == username,
            OracleReports.report_id == report_id,
        )
        result = session.execute(stmt)
        report = result.scalar_one_or_none()
        if report:
            session.delete(report)
            session.commit()
            return JSONResponse(status_code=200, content={"message": "Report deleted"})
        else:
            return JSONResponse(status_code=404, content={"error": "Report not found"})


@router.post("/oracle/rename_report")
async def rename_report(req: Request):
    """
    Given a report_id and a new report_name, this endpoint will rename the report,
    and re-export the pdf with the new name in the title.
    """
    body = await req.json()
    # TODO: Implement this endpoint
    return JSONResponse(status_code=501, content={"error": "Not Implemented"})


@router.post("/oracle/feedback_report")
async def feedback_report(req: Request):
    """
    Given a report id and the associated feedback, save the feedback with the report.
    """
    body = await req.json()
    # TODO: Implement this endpoint
    return JSONResponse(status_code=501, content={"error": "Not Implemented"})


@router.post("/oracle/clarify_report")
async def clarify_report(req: Request):
    """
    This endpoint receives the clarification response from the user.
    If it is empty, the clarification is assumed to be dismissed / resolved and
    we save that information.
    If it is not empty, we will update the associated clarification question's
    response and continue the generation process if no clarifications are left
    unaddressed.
    """
    body = await req.json()
    # TODO: Implement this endpoint
    return JSONResponse(status_code=501, content={"error": "Not Implemented"})


@router.post("/oracle/test_stage")
async def oracle_test_stage(req: Request):
    """
    [TEST ROUTE]: this route is only for testing purposes and should not be used in production.
    Given the question / objective statement provided by the user, this endpoint
    will return a summary of the data, including a table and chart.
    We keep this route flexible to facilitate faster testing of each stage
    """
    body = await req.json()
    for field in ["api_key", "inputs", "outputs", "task_type", "stage"]:
        if field not in body:
            return JSONResponse(
                status_code=400,
                content={"error": "Bad Request", "message": f"Missing '{field}' field"},
            )
    stage = body.get("stage", "explore")
    if stage == TaskStage.GATHER_CONTEXT.value:
        response = await gather_context(
            api_key=body["api_key"],
            username=body.get("username", ""),
            inputs=body.get("inputs", {}),
            report_id=int(body.get("report_id", "1")),
            task_type=TaskType(body.get("task_type", TaskType.EXPLORATION.value)),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)
    elif stage == TaskStage.EXPLORE.value:
        response = await explore_data(
            api_key=body["api_key"],
            username=body.get("username", ""),
            report_id=int(body.get("report_id", "1")),
            task_type=TaskType(body.get("task_type", TaskType.EXPLORATION.value)),
            inputs=body.get("inputs", {}),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)
    elif stage == TaskStage.PREDICT.value:
        response = await predict(
            api_key=body["api_key"],
            username=body.get("username", ""),
            report_id=int(body.get("report_id", "1")),
            task_type=TaskType(body.get("task_type", TaskType.PREDICTION.value)),
            inputs=body.get("inputs", {}),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)

    elif stage == TaskStage.OPTIMIZE.value:
        """
        Generates an optimization task based on explore and gather_context stage's outputs.

        Inputs:
        - api_key: str
        - gather_context: dict - Results of the gather_context stage. As saved in the dict while running stage_execute.
        - explore: dict - Results of the explore stage. As saved in the dict while running stage_execute.

        It will use the above results, and construct them into a prompt. We will then pass it to an LLM to get a JSON back.

        Output: A well defined optimization task, which can be of type `simple_recommendation` or `run_optimizer_model`.
        """
        api_key = body.get("api_key", None)
        outputs = body.get("outputs", {})
        task_type = body.get("task_type", TaskType.OPTIMIZATION.value)
        question = body.get("question", None)
        username = body.get("username", None)
        report_id = body.get("report_id", None)

        res = await optimize(
            api_key=api_key,
            username=username,
            report_id=report_id,
            task_type=TaskType(task_type),
            inputs={"user_question": question},
            outputs=outputs,
        )
        return JSONResponse(content=res)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": f"Invalid 'stage' field. Must be one of: {TaskStage.__members__.keys()}",
            },
        )
