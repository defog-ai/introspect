import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils import longest_substring_overlap
from db_utils import OracleReports, engine, get_report_data, redis_client, validate_user
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from generic_utils import get_api_key_from_key_name, make_request
from oracle.constants import TaskStage, TaskType
from oracle.core import (
    begin_generation_task,
    gather_context,
    predict,
)
from oracle.explore import explore_data
from oracle.optimize import optimize
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import insert

from oracle.optimize import optimize
from oracle.explore import explore_data
from oracle.core import generate_report, gather_context, predict
from db_utils import OracleReports, engine, validate_user
from generic_utils import get_api_key_from_key_name, make_request
from utils_logging import LOGGER, save_and_log, save_timing

router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


class ClarifyQuestionRequest(BaseModel):
    key_name: str
    token: str
    user_question: str
    task_type: Optional[TaskType] = None
    answered_clarifications: List[Dict[str, Any]] = []

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "key_name": "my_api_key",
                    "token": "user_token",
                    "user_question": "What are the sales trends?",
                    "task_type": None,
                    "answered_clarifications": [],
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


class GenerateAnalysis(BaseModel):
    report_id: int
    token: str
    key_name: str
    previous_analyses: list
    new_analysis_question: str


@router.post("/oracle/generate_analysis")
async def generate_analysis(req: GenerateAnalysis):
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

    # get report's data
    # send a request to this server's own endpoint /oracle/get_report_data
    report_data = get_report_data(req.report_id, api_key)

    if "error" in report_data:
        return JSONResponse(status_code=404, content=report_data)

    report_data = report_data["data"]

    LOGGER.debug(f"Previous analyses: {req.previous_analyses}")

    # Call explore_data with a single analysis request
    # We'll reuse the explore_data function but with a single question
    inputs = {
        "user_question": req.new_analysis_question,
        "sources": report_data["inputs"].get("sources", []),
        "max_analyses": 1,
        "max_rounds": 1,
        "previous_analyses": req.previous_analyses,
    }

    # Reuse the outputs from the parent analyses to maintain context
    outputs = {
        "gather_context": report_data["outputs"].get("gather_context", {}),
        "explore": report_data["outputs"].get("explore", {}),
    }

    # also change the problem statement to the new analysis question
    outputs["gather_context"]["problem_statement"] = req.new_analysis_question

    result = await explore_data(
        api_key=api_key,
        report_id=str(req.report_id),
        task_type=TaskType.EXPLORATION,
        inputs=inputs,
        outputs=outputs,
    )

    if "error" in result or "analyses" not in result or len(result["analyses"]) == 0:
        return JSONResponse(
            status_code=500, content={"error": "Error generating analysis"}
        )

    full_context_with_previous_analyses = result.get(
        "full_context_with_previous_analyses", []
    )

    analysis = result["analyses"][0]

    # generate mdx for this analysis
    mdx = await make_request(
        DEFOG_BASE_URL + "/oracle/generate_analysis_mdx",
        {
            "api_key": api_key,
            "problem_statement": req.new_analysis_question,
            "task_type": TaskType.EXPLORATION.value,
            "analysis": analysis,
            "context": full_context_with_previous_analyses,
        },
    )

    return {
        "analysis": analysis,
        "mdx": mdx,
    }


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
        args=[api_key, report_id, req.task_type, user_inputs]
    )
    return JSONResponse(content={"report_id": report_id, "status": "started"})


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
