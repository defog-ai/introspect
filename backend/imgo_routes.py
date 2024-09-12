
from fastapi import APIRouter, Request
from generic_utils import (
    make_request,
    get_api_key_from_key_name,
)
from db_utils import validate_user, get_db_type_creds
import os
from fastapi.responses import JSONResponse

router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


async def send_imgo_request(
    request: Request, endpoint: str, additional_payload: dict = None
):
    """Helper function to handle IMGO request processing."""
    params = await request.json()
    token = params.get("token")
    if not validate_user(token):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    key_name = params.get("key_name")
    optimized_glossary = params.get("optimized_glossary", None)
    optimized_metadata = params.get("optimized_metadata", None)

    api_key = get_api_key_from_key_name(key_name)
    db_type, _ = get_db_type_creds(api_key)

    payload = {
        "api_key": api_key,
        "db_type": db_type,
        "optimized_glossary": optimized_glossary,
        "optimized_metadata": optimized_metadata,
    }

    if additional_payload:
        payload.update(additional_payload)

    url = f"{DEFOG_BASE_URL}/{endpoint}"
    return await make_request(url, data=payload)


@router.post("/generate_golden_queries_from_questions")
async def generate_golden_queries_from_questions(request: Request):
    """Generates golden queries for the current set of golden questions."""
    return await send_imgo_request(request, "imgo_gen_golden_queries")


@router.post("/check_generated_golden_queries_validity")
async def check_generated_golden_queries_validity(request: Request):
    """Checks if the generated golden queries are valid and returns the invalid ones with the error message."""
    return await send_imgo_request(request, "imgo_check_golden_queries_valid")


@router.post("/check_generated_golden_queries_correctness")
async def check_generated_golden_queries_correctness(request: Request):
    """Checks if the generated golden queries are correct and returns a confirmation message that it was triggered."""
    return await send_imgo_request(request, "imgo_check_golden_queries_correct")


@router.post("/optimize_glossary")
async def optimize_glossary(request: Request):
    """Responds to a request for optimized glossary and returns the optimized glossary."""
    return await send_imgo_request(request, "imgo_optimize_glossary")


@router.post("/optimize_metadata")
async def optimize_metadata(request: Request):
    """Responds to a request for optimized metadata and returns the optimized metadata."""
    return await send_imgo_request(request, "imgo_optimize_metadata")


@router.post("/get_recommendation_for_glossary_and_metadata")
async def get_recommendation_for_glossary_and_metadata(request: Request):
    """Responds to a recommendation request for whether to improve glossary and/or metadata."""
    res = await send_imgo_request(request, "imgo_get_recommendation")

    # Initialize flags to indicate if optimization is recommended
    res["is_glossary_optimization_recommended"] = False
    res["is_metadata_optimization_recommended"] = False

    # Check if the message suggests optimizing glossary or metadata
    if "message" in res and res["message"]:
        message = str(res["message"]).lower()
        if "glossary" in message:
            res["is_glossary_optimization_recommended"] = True
        if "metadata" in message:
            res["is_metadata_optimization_recommended"] = True

    return res



@router.post("/check_task_status")
async def check_task_status(request: Request):
    """Checks the status of a task and returns the status which can be either 'processing' or 'completed'."""
    print("Checking task status")
    params = await request.json()
    token = params.get("token")
    if not validate_user(token):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)

    task_id = params.get("task_id")

    url = f"{DEFOG_BASE_URL}/check_imgo_task_status"
    return await make_request(
        url,
        data={"api_key": api_key, "task_id": task_id},
    )
