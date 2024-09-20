from datetime import datetime
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import insert, select

from oracle.explore import explore_data
from oracle.core import gather_context
from db_utils import OracleReports, engine, validate_user
from generic_utils import get_api_key_from_key_name, make_request
from oracle.core import (
    EXPLORATION,
    TASK_TYPES,
    begin_generation_task,
    get_report_file_path,
)

router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


@router.post("/oracle/clarify_question")
async def clarify_question(req: Request):
    """
    Given the question / objective statement provided by the user, this endpoint
    will return:
        clarifications: list[str]
        task_type: str
        ready: bool
    Depending on the task type, the endpoint will return other additional fields.
    Note that our UX has only been designed to display the clarifications, task_type,
    and ready indicator for now. All other fields are not used by the client.
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
    response = await make_request(DEFOG_BASE_URL + "/oracle/clarify_task_type", body)
    task_type = response.get("task_type", "")
    print(f"Task type: {task_type}")
    body["task_type"] = task_type
    response = await make_request(DEFOG_BASE_URL + "/oracle/clarify", body)
    response["task_type"] = task_type
    return JSONResponse(content=response)


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


@router.post("/oracle/begin_generation")
async def begin_generation(req: Request):
    """
    Given the question / objective statement provided by the user, as well as the
    full list of configuration options, this endpoint will begin the process of
    generating a report asynchronously as a celery task.
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
    if "user_question" not in body:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "Missing 'user_question' field",
            },
        )
    if "task_type" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": "Bad Request", "message": "Missing 'task_type' field"},
        )
    task_type = body["task_type"]
    if task_type not in TASK_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": f"Invalid 'task_type' field. Must be one of: {TASK_TYPES}",
            },
        )
    if "sources" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": "Bad Request", "message": "Missing 'sources' field"},
        )
    elif not isinstance(body["sources"], list):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "'sources' field must be a list",
            },
        )
    # insert a new row into the OracleReports table and get a new report_id
    with Session(engine) as session:
        stmt = (
            insert(OracleReports)
            .values(
                api_key=api_key,
                username=username,
                inputs=body,
                status="started",
                created_ts=datetime.now(),
            )
            .returning(OracleReports.report_id)
        )
        result = session.execute(stmt)
        report_id = result.scalar_one()
        session.commit()
    begin_generation_task.apply_async(
        args=[api_key, username, report_id, task_type, body]
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
    """
    body = await req.json()
    for field in ["api_key", "inputs", "outputs"]:
        if field not in body:
            return JSONResponse(
                status_code=400,
                content={"error": "Bad Request", "message": f"Missing '{field}' field"},
            )
    stage = body.get("stage", "explore")
    if stage == "gather_context":
        response = await gather_context(
            api_key=body["api_key"],
            username=body.get("username", ""),
            inputs=body.get("inputs", {}),
            report_id=int(body.get("report_id", "1")),
            task_type=body.get("task_type", EXPLORATION),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)
    elif stage == "explore":
        response = await explore_data(
            api_key=body["api_key"],
            username=body.get("username", ""),
            report_id=int(body.get("report_id", "1")),
            task_type=body.get("task_type", EXPLORATION),
            inputs=body.get("inputs", {}),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": f"Invalid 'stage' field. Must be one of: ['gather_context', 'explore']",
            },
        )
