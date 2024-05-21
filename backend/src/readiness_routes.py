from fastapi import APIRouter, Request
import json
import os
from auth_utils import validate_user
from generic_utils import make_request
from defog import Defog

DEFOG_API_KEY = os.environ["DEFOG_API_KEY"]  # replace with your DEFOG_API_KEY
DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")

router = APIRouter()


@router.post("/readiness/basic")
async def check_basic_readiness(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev")
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    metadata_ready = False
    golden_queries_ready = False
    glossary_ready = False

    r = await make_request(
        f"{DEFOG_BASE_URL}/get_metadata", {"api_key": DEFOG_API_KEY, "dev": dev}
    )

    if r["table_metadata"]:
        metadata_ready = True
    if r["glossary"]:
        glossary_ready = True

    r = await make_request(
        f"{DEFOG_BASE_URL}/get_golden_queries", {"api_key": DEFOG_API_KEY, "dev": dev}
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
    dev = params.get("dev")
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    defog = Defog()
    db_type = defog.db_type

    resp = await make_request(
        f"{DEFOG_BASE_URL}/check_gold_queries_valid",
        json={"api_key": DEFOG_API_KEY, "db_type": db_type, "dev": dev},
    )
    return resp


@router.post("/readiness/check_instruction_consistency")
async def check_glossary_consistency(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev")
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    resp = await make_request(
        f"{DEFOG_BASE_URL}/check_glossary_consistency",
        json={"api_key": DEFOG_API_KEY, "dev": dev},
    )
    return resp


@router.post("/readiness/check_golden_query_coverage")
async def check_golden_query_coverage(request: Request):
    params = await request.json()
    token = params.get("token")
    dev = params.get("dev")
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    defog = Defog()
    db_type = defog.db_type

    resp = await make_request(
        f"{DEFOG_BASE_URL}/get_golden_queries_coverage",
        json={"api_key": DEFOG_API_KEY, "dev": dev, "db_type": db_type},
    )
    return resp
