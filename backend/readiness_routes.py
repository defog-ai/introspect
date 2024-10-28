from fastapi import APIRouter, Request
import os
from utils_logging import LOGGER
from utils_validation import validate_queries
from db_utils import validate_user, get_db_type_creds
from generic_utils import make_request, get_api_key_from_key_name
from fastapi.responses import JSONResponse

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")

router = APIRouter()


@router.post("/readiness/basic")
async def check_basic_readiness(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev", False)
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)

    metadata_ready = False
    golden_queries_ready = False
    glossary_ready = False

    r = await make_request(
        f"{DEFOG_BASE_URL}/get_metadata", {"api_key": api_key, "dev": dev}
    )

    if r["table_metadata"]:
        metadata_ready = True
    if r["glossary"]:
        glossary_ready = True

    r = await make_request(
        f"{DEFOG_BASE_URL}/get_golden_queries", {"api_key": api_key, "dev": dev}
    )

    if r["golden_queries"] and len(r["golden_queries"]) > 0:
        golden_queries_ready = True

    return {
        "success": True,
        "metadata": metadata_ready,
        "golden_queries": golden_queries_ready,
        "glossary": glossary_ready,
    }


@router.post("/readiness/check_golden_queries_validity")
async def check_golden_queries_validity(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev", False)
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    resp = await make_request(
        f"{DEFOG_BASE_URL}/check_gold_queries_valid",
        data={"api_key": api_key, "db_type": db_type, "dev": dev},
    )
    return resp


@router.post("/readiness/check_instruction_consistency")
async def check_glossary_consistency(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)

    resp = await make_request(
        f"{DEFOG_BASE_URL}/check_glossary_consistency",
        data={"api_key": api_key, "dev": dev},
    )
    return resp


@router.post("/readiness/check_golden_query_coverage")
async def check_golden_query_coverage(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    resp = await make_request(
        f"{DEFOG_BASE_URL}/get_golden_queries_coverage",
        data={"api_key": api_key, "dev": dev, "db_type": db_type},
    )
    return resp


@router.post("/readiness/regression_results")
async def regression_results(request: Request):
    """
    Takes in the api key and for each golden query, regenerates the SQL
    and compares it with the golden query SQL, sending back the results.
    The output contains the average correct rate, the average subset correct rate,
    and `reference_queries`, which is a list of dictionaries, each containing:
    - question: str
    - sql_golden: str (the golden SQL)
    - sql_gen: str (the generated SQL)
    - correct: bool (whether the generated SQL produced the exact same results as the golden SQL)
    - subset: bool (whether the generated SQL produced a subset of the results of the golden SQL)
    - source: str (either "golden" or "feedback")
    """
    params = await request.json()
    token = params.get("token")
    if not validate_user(token, user_type="admin"):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    key_name = params.get("key_name")
    queries = params.get("queries", [])

    api_key = get_api_key_from_key_name(key_name)
    res = get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return JSONResponse(
            {"error": "No db creds found. Please add db creds for this api key."},
            status_code=400,
        )

    LOGGER.debug(f"[RegressionTesting] - api_key: {api_key}")
    LOGGER.debug(f"[RegressionTesting] - queries: {queries}")

    query_validation_result = await validate_queries(
        api_key=api_key, db_type=db_type, db_creds=db_creds, queries=queries
    )

    return {
        "total": query_validation_result["total"],
        "correct": query_validation_result["correct"],
        "results": query_validation_result["results"],
        "query_wise_results": query_validation_result["query_wise_results"],
    }
