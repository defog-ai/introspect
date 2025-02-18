import traceback
from auth_utils import validate_user_request
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from llm_api import O3_MINI
from request_models import GenerateSQLQueryRequest
from utils_sql import generate_sql_query
from utils_logging import LOGGER
from llm_api import O3_MINI


router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Query Generation"],
)


@router.post("/generate_sql_query")
async def generate_sql_query_route(request: GenerateSQLQueryRequest):
    """
    Generate a chat response based on a query.
    """
    try:
        resp = await generate_sql_query(
            question=request.question,
            db_name=request.db_name,
            db_type=request.db_type,
            metadata=request.metadata,
            instructions=request.instructions,
            previous_context=request.previous_context,
            hard_filters=request.hard_filters,
            num_golden_queries=request.num_golden_queries,
            model_name=request.model_name or O3_MINI,
        )
        if resp is None:
            return JSONResponse(
                status_code=500, content={"error": "Error generating SQL query"}
            )
        sql = resp["sql"]
        error = resp.get("error", None)
        return {
            "sql": sql,
            "error": error,
        }
    except Exception as e:
        LOGGER.error(f"[generate_sql_query] ERROR: {e}")
        LOGGER.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})
