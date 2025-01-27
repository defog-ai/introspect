import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from utils import longest_substring_overlap
from db_utils import (
    OracleGuidelines,
    OracleReports,
    add_or_update_analysis,
    delete_analysis,
    engine,
    get_analysis_status,
    get_report_data,
    redis_client,
    update_summary_dict,
    validate_user,
    get_multiple_analyses,
)
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from generic_utils import get_api_key_from_key_name, make_request
from oracle.constants import TaskStage, TaskType
from oracle.core import (
    generate_report,
    begin_generation_task,
    gather_context,
    predict,
)
from oracle.explore import explore_data
from oracle.optimize import optimize
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import insert, update

from db_utils import OracleReports, engine, validate_user
from generic_utils import get_api_key_from_key_name, make_request
from utils_logging import LOGGER, save_and_log, save_timing
from oracle.redis_utils import (
    get_analysis_task_id,
    delete_analysis_task_id,
    store_analysis_task_id,
)
from oracle.celery_app import celery_app
from oracle.core import generate_analysis_task


router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


class ClarificationGuidelinesRequest(BaseModel):
    api_key: str
    clarification_guidelines: str


@router.post("/oracle/set_clarification_guidelines")
async def set_clarification_guidelines(req: ClarificationGuidelinesRequest):
    with Session(engine) as session:
        with session.begin():
            session.execute(
                update(OracleGuidelines).values(
                    clarification_guidelines=req.clarification_guidelines
                )
            )

class GetClarificationGuidelinesRequest(BaseModel):
    key_name: str

@router.post("/oracle/get_clarification_guidelines")
async def get_clarification_guidelines(req: GetClarificationGuidelinesRequest):
    api_key = get_api_key_from_key_name(req.key_name)
    stmt = select(OracleGuidelines).where(OracleGuidelines.api_key == api_key)
    with Session(engine) as session:
        result = session.execute(stmt)
        result = result.scalar_one_or_none()
        if not result:
            return JSONResponse(status_code=404, content={"error": "Guidelines not found"})
        return JSONResponse(content={"clarification_guidelines": result.clarification_guidelines})

class ClarifyQuestionRequest(BaseModel):
    key_name: str
    token: str
    user_question: str
    task_type: Optional[TaskType] = None
    answered_clarifications: List[Dict[str, Any]] = []
    clarification_guidelines: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "key_name": "my_api_key",
                    "token": "user_token",
                    "user_question": "What are the sales trends?",
                    "task_type": None,
                    "answered_clarifications": [],
                    "clarification_guidelines": "If unspecified, trends should be cover the last 3 years on a monthly basis.",
                }
            ]
        }
    }


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
    username = await validate_user(req.token, user_type=None, get_username=True)
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

    # fetch the latest question asked by the user from redis.
    # if the latest question has a longest substring match of over 75% with the
    # latest question, we will use the task_type from the latest question.
    # else we will infer the task_type from the current question.
    latest_question = redis_client.get(f"{api_key}:oracle:user_question")
    LOGGER.debug(f"Latest question: {latest_question}")
    min_overlap_length = len(req.user_question) * 0.75
    if latest_question:
        overlaps, overlap_str = longest_substring_overlap(
            latest_question, req.user_question, min_overlap_length
        )
        LOGGER.debug(f"Overlaps: {overlaps}, overlap_str: {overlap_str}")
        if not overlaps:
            req.task_type = None
    else:
        # if there hasn't been a recent question asked, always reinfer instead of reusing
        req.task_type = None

    if not req.task_type:
        clarify_task_type_request = {
            "api_key": api_key,
            "user_question": req.user_question,
        }
        try:
            clarify_task_type_response = await make_request(
                DEFOG_BASE_URL + "/oracle/clarify_task_type", clarify_task_type_request
            )
            task_type_str = clarify_task_type_response["task_type"]
            redis_key = f"{api_key}:oracle:user_question"
            redis_client.set(
                redis_key, req.user_question, ex=60
            )  # store the question for 60 seconds
            LOGGER.debug(
                f"Inferred task type: {task_type_str}\nSaved to redis key {redis_key}"
            )
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
        task_type_str = req.task_type.value
        LOGGER.debug(f"Reusing existing task type: {task_type_str}")
    LOGGER.debug(f"Task type: {task_type_str}")
    ts = save_timing(ts, "get_task_type", timings)
    clarify_request = {
        "api_key": api_key,
        "user_question": req.user_question,
        "task_type": task_type_str,
        "answered_clarifications": req.answered_clarifications,
    }
    if req.clarification_guidelines:
        clarify_request["clarification_guidelines"] = req.clarification_guidelines
        # save to oracle_guidelines table, overwriting if already exists
        async with AsyncSession(engine) as session:
            async with session.begin():
                # check if the api_key already exists
                result = await session.execute(
                    select(OracleGuidelines).where(OracleGuidelines.api_key == api_key)
                )
                if result.scalar_one_or_none():
                    await session.execute(
                        update(OracleGuidelines).values(
                            api_key=api_key,
                            clarification_guidelines=req.clarification_guidelines,
                        )
                    )
                else:
                    await session.execute(
                        insert(OracleGuidelines).values(
                            api_key=api_key,
                            clarification_guidelines=req.clarification_guidelines,
                        )
                    )
                LOGGER.debug(f"Saved clarification guidelines to DB for API key {api_key}")
    else:
        LOGGER.debug("No clarification guidelines provided, retrieving from DB")
        async with AsyncSession(engine) as session:
            async with session.begin():
                result = await session.execute(
                    select(OracleGuidelines.clarification_guidelines).where(OracleGuidelines.api_key == api_key)
                )
                guidelines = result.scalar_one_or_none()
                if not guidelines:
                    LOGGER.warning("No clarification guidelines found in DB")
                else:
                    LOGGER.debug(f"Retrieved clarification guidelines from DB: {guidelines}")
                    clarify_request["clarification_guidelines"] = guidelines
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
    clarify_response["task_type"] = task_type_str
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
    username = await validate_user(token, user_type=None, get_username=True)
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
    hard_filters: Optional[List[Dict[str, str]]] = []

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "key_name": "my_api_key",
                    "token": "user_token",
                    "user_question": "What are the sales trends?",
                    "task_type": "analysis",
                    "sources": ["source1", "source2"],
                    "clarifications": [{"question": "answer"}],
                }
            ]
        }
    }


class AnalysisRequest(BaseModel):
    report_id: int
    token: str
    key_name: str
    analysis_id: Optional[str] = None
    recommendation_idx: Optional[int] = None


class GenerateAnalysis(AnalysisRequest):
    previous_analysis_ids: list[str]
    new_analysis_question: str
    recommendation_idx: int = -1


@router.post("/oracle/get_analysis_status")
async def get_analysis_status_endpoint(req: AnalysisRequest):
    username = await validate_user(req.token, user_type=None, get_username=True)

    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    api_key = get_api_key_from_key_name(req.key_name)

    err, status = await get_analysis_status(
        api_key=api_key,
        analysis_id=req.analysis_id,
        report_id=req.report_id,
    )

    if err:
        return JSONResponse(status_code=500, content={"error": err})

    return JSONResponse(content={"status": status})


@router.post("/oracle/delete_analysis")
async def delete_analysis_endpoint(req: AnalysisRequest):
    """
    Deletes an analysis given an analysis_id.
    If recommendation_idx is provided, deletes the analysis for that recommendation.
    Also cancels any running Celery task for this analysis.
    """
    username = await validate_user(req.token, user_type=None, get_username=True)

    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    api_key = get_api_key_from_key_name(req.key_name)

    # First try to cancel any running task
    task_id = get_analysis_task_id(req.analysis_id)
    if task_id:
        try:
            celery_app.control.revoke(task_id, terminate=True)
            delete_analysis_task_id(req.analysis_id)
            LOGGER.info(f"Cancelled task {task_id} for analysis {req.analysis_id}")
        except Exception as e:
            LOGGER.error(f"Error cancelling task {task_id}: {str(e)}")

    err = await delete_analysis(
        api_key=api_key,
        analysis_id=req.analysis_id,
        report_id=req.report_id,
    )

    if err:
        return JSONResponse(status_code=500, content={"error": err})

    # update summary dict if applicable
    if req.recommendation_idx is not None:
        summary_dict = (
            (await get_report_data(req.report_id, api_key))
            .get("data", {})
            .get("outputs", {})
            .get(TaskStage.EXPORT.value, {})
            .get("executive_summary", None)
        )

        if summary_dict:
            curr_refs = summary_dict["recommendations"][req.recommendation_idx][
                "analysis_reference"
            ]
            if not curr_refs or type(curr_refs) != list:
                curr_refs = []
            if req.analysis_id in curr_refs:
                curr_refs.remove(req.analysis_id)
                summary_dict["recommendations"][req.recommendation_idx][
                    "analysis_reference"
                ] = curr_refs
                await update_summary_dict(api_key, req.report_id, summary_dict)

    return JSONResponse(content={"message": "Analysis deleted"})


@router.post("/oracle/generate_analysis")
async def generate_analysis(req: GenerateAnalysis):
    username = await validate_user(req.token, user_type=None, get_username=True)

    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    api_key = get_api_key_from_key_name(req.key_name)
    analysis_id = req.analysis_id or str(uuid4())

    # start an empty analysis
    err = await add_or_update_analysis(
        api_key=api_key,
        report_id=int(req.report_id),
        analysis_id=analysis_id,
        analysis_json={
            # initialise the title to just the question for now
            "title": req.new_analysis_question,
            "analysis_id": analysis_id,
        },
        status="STARTED",
        mdx=None,
    )

    if err:
        return JSONResponse(status_code=500, content={"error": err})

    # get report's data
    report_data = await get_report_data(req.report_id, api_key)

    if "error" in report_data:
        return JSONResponse(status_code=404, content=report_data)

    report_data = report_data["data"]

    # Get previous analyses data
    err, previous_analyses = await get_multiple_analyses(
        analysis_ids=req.previous_analysis_ids,
        columns=["analysis_id", "analysis_json", "status"],
    )

    if err:
        return JSONResponse(status_code=500, content={"error": err})

    # Filter out any analyses that are not complete
    previous_analyses = [
        analysis["analysis_json"]
        for analysis in previous_analyses
        if analysis["status"] == "DONE"
    ]

    # update summary dict
    summary_dict = (
        report_data.get("outputs", {})
        .get(TaskStage.EXPORT.value, {})
        .get("executive_summary", None)
    )

    if summary_dict:
        curr_refs = summary_dict["recommendations"][req.recommendation_idx][
            "analysis_reference"
        ]
        if not curr_refs or type(curr_refs) != list:
            curr_refs = []
        curr_refs.append(analysis_id)
        summary_dict["recommendations"][req.recommendation_idx][
            "analysis_reference"
        ] = curr_refs
        await update_summary_dict(
            api_key=api_key, report_id=req.report_id, summary_dict=summary_dict
        )

    LOGGER.debug(f"Summary dict updated for report {req.report_id}")

    # Start the Celery task
    task = generate_analysis_task.delay(
        api_key=api_key,
        report_id=int(req.report_id),
        analysis_id=analysis_id,
        new_analysis_question=req.new_analysis_question,
        recommendation_idx=req.recommendation_idx,
        previous_analyses=previous_analyses,
    )

    # Store the task ID in Redis
    store_analysis_task_id(analysis_id, task.id)

    return JSONResponse(
        content={"status": "started", "analysis_id": analysis_id, "task_id": task.id}
    )


@router.post("/oracle/begin_generation")
async def begin_generation(req: BeginGenerationRequest):
    """
    Given the question / objective statement provided by the user, as well as the
    full list of configuration options, this endpoint will begin the process of
    generating a report asynchronously as a celery task.
    """
    username = await validate_user(req.token, user_type=None, get_username=True)
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
        "hard_filters": req.hard_filters,
    }
    async with AsyncSession(engine) as session:
        async with session.begin():
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
            result = await session.execute(stmt)
            report_id = result.scalar_one()
    begin_generation_task.apply_async(
        args=[api_key, report_id, req.task_type, user_inputs]
    )
    return JSONResponse(content={"report_id": report_id, "status": "started"})


class CommentsWithRelevantText(BaseModel):
    comment_text: str
    relevant_text: str


class ReviseReportRequest(BaseModel):
    """
    Request model for updating the report based on the comments.
    """

    report_id: int
    token: str
    key_name: str
    comments_with_relevant_text: list[CommentsWithRelevantText]
    general_comments: str


@router.post("/oracle/revise_report")
async def revision(req: ReviseReportRequest):
    """
    Given a report_id, this endpoint will submit the report for revision based on the comments passed.
    """
    username = await validate_user(req.token, user_type=None, get_username=True)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "message": "Invalid username or password",
            },
        )

    api_key = get_api_key_from_key_name(req.key_name)

    # if comment length is 0 and general comments is empty, return an error
    if not len(req.comments_with_relevant_text) and not req.general_comments:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "No comments or general comments provided",
            },
        )

    """
    We will reuse the begin generation task to handle the new report's generation. (The handling of the fact that this is a revision is handled inside the explore stage)

    In addition to the report's existing inputs, we will pass (within the inputs dictionary) the following keys:
    - comments: list of comments from the user
    - general_comments: general comments from the user
    - is_revision: flag to indicate that the report is being revised
    """

    # get the report's data
    report_data = await get_report_data(req.report_id, api_key)
    if (
        "error" in report_data
        or "data" not in report_data
        or "inputs" not in report_data["data"]
    ):
        return JSONResponse(status_code=404, content=report_data)

    report_data = report_data["data"]
    status = report_data["status"]

    is_being_revised = status.startswith("Revision in progress: ")
    is_revision = status.startswith("Revision: ")

    # if, by some chance, this report is a temporary revision report, return an error
    # this is a massive edge case. should never happen because we don't expose temporary revision reports on the front end

    if is_revision:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "We cannot revise this report.",
            },
        )

    # if report's status is either not done, or starts with "Revision in progress", return an error
    if status != "done" and not status.startswith("Revision in progress"):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "Report is not done or is being revised",
            },
        )

    # insert required data for revision into the inputs
    inputs_with_comments = report_data["inputs"]
    inputs_with_comments["comments"] = [
        comment.model_dump() for comment in req.comments_with_relevant_text
    ]
    inputs_with_comments["general_comments"] = req.general_comments
    inputs_with_comments["is_revision"] = True
    inputs_with_comments["original_analyses"] = (
        report_data.get("outputs", {})
        .get(TaskStage.EXPLORE.value, {})
        .get("analyses", [])
    )
    inputs_with_comments["original_report_mdx"] = (
        report_data.get("outputs", {}).get(TaskStage.EXPORT.value, {}).get("mdx", "")
    ).strip()

    inputs_with_comments["original_report_id"] = req.report_id

    LOGGER.info(f"Submitting report {req.report_id} for revision")
    LOGGER.info(f"{req.general_comments}")
    LOGGER.info(inputs_with_comments["comments"])

    if not inputs_with_comments["original_report_mdx"]:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "Original report mdx is empty",
            },
        )

    # now, create a new report
    # this is so that if the revision fails, the original report is not lost
    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = (
                insert(OracleReports)
                .values(
                    api_key=api_key,
                    username=username,
                    inputs=inputs_with_comments,
                    status="Revision: started",
                    created_ts=datetime.now(),
                )
                .returning(OracleReports.report_id)
            )
            result = await session.execute(stmt)
            report_id = result.scalar_one()

    # set the status of the original report to "Revision in progress"
    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = (
                update(OracleReports)
                .where(OracleReports.report_id == req.report_id)
                .values(status=f"Revision in progress")
            )
            await session.execute(stmt)

    begin_generation_task.apply_async(
        args=[api_key, report_id, TaskType.EXPLORATION.value, inputs_with_comments]
    )

    return JSONResponse(
        status_code=200, content={"message": "Report submitted for revision"}
    )


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
            inputs=body.get("inputs", {}),
            report_id=int(body.get("report_id", "1")),
            task_type=TaskType(body.get("task_type", TaskType.EXPLORATION.value)),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)
    elif stage == TaskStage.EXPLORE.value:
        response = await explore_data(
            api_key=body["api_key"],
            report_id=int(body.get("report_id", "1")),
            task_type=TaskType(body.get("task_type", TaskType.EXPLORATION.value)),
            inputs=body.get("inputs", {}),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)
    elif stage == TaskStage.PREDICT.value:
        response = await predict(
            api_key=body["api_key"],
            report_id=int(body.get("report_id", "1")),
            task_type=TaskType(body.get("task_type", TaskType.PREDICTION.value)),
            inputs=body.get("inputs", {}),
            outputs=body.get("outputs", {}),
        )
        return JSONResponse(response)

    elif stage == TaskStage.OPTIMIZE.value:
        """
        Generates an optimization task, runs it, and generates recommendations. All three are done based on explore and gather_context stage's outputs.

        Inputs:
        - api_key: str
        - gather_context: dict - Results of the gather_context stage. As saved in the dict while running stage_execute.
        - explore: dict - Results of the explore stage. As saved in the dict while running stage_execute.

        Output: The outputs of the optimization stage. An object with keys:
        - processed_items: dict - The various processing steps done to run the task.
        - recommendations: list[str] - This is a list of strings, generated by feeding the outputs above + the other stage's outputs to an LLM.
        """
        api_key = body.get("api_key", None)
        outputs = body.get("outputs", {})
        task_type = body.get("task_type", TaskType.OPTIMIZATION.value)
        report_id = body.get("report_id", None)

        res = await optimize(
            api_key=api_key,
            report_id=report_id,
            task_type=TaskType(task_type),
            inputs={},
            outputs=outputs,
        )
        return JSONResponse(content=res)
    elif stage == TaskStage.EXPORT.value:
        api_key = body.get("api_key", None)
        outputs = body.get("outputs", {})
        inputs = body.get("inputs", {})
        task_type = body.get("task_type", "")
        report_id = body.get("report_id", None)
        res = await generate_report(
            api_key=api_key,
            report_id=report_id,
            task_type=TaskType(task_type),
            inputs=inputs,
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
