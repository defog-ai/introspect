from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auth_utils import validate_user
from generic_utils import get_api_key_from_key_name
from utils_xdb import xdb_query

router = APIRouter()


@router.post("/xdb/query")
async def xdb_query_route(request: Request):
    """
    [Testing]
    Route for testing internal xdb querying
    """
    body = await request.json()
    api_key = body.get("api_key")
    if not api_key:
        token = body.get("token")
        key_name = body.get("key_name")
        user = await validate_user(token)
        api_key = await get_api_key_from_key_name(key_name)
        if not user:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Invalid username or password",
                },
            )
    question = body.get("question")
    return_debug = body.get("return_debug", False)

    result = await xdb_query(api_key, question, return_debug)

    return result
