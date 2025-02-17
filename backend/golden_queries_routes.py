from auth_utils import validate_user_request
from db_utils import engine
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from request_models import GoldenQueriesDeleteRequest, GoldenQueriesUpdateRequest, UserRequest
import traceback
from utils_logging import LOGGER
from utils_embedding import get_embedding
from utils_golden_queries import get_all_golden_queries, set_golden_query, delete_golden_query

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Golden Queries"],
)


@router.post("/integration/get_golden_queries")
async def get_golden_queries_route(request: UserRequest):
    try:
        golden_queries = await get_all_golden_queries(request.db_name)
        golden_queries = [{"question": r.question, "sql": r.sql} for r in golden_queries]
        return {"golden_queries": golden_queries}
    except Exception as e:
        LOGGER.error(f"Error getting golden queries: {e}")
        LOGGER.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/integration/update_golden_queries")
async def update_golden_queries_route(request: GoldenQueriesUpdateRequest):
    """
    Updates a list of golden queries for a given db_name.
    If a golden query's question already exists under the same db_name,
    it will be updated with the new sql.
    Else, a new golden query will be added to the database.
    This effectively means that we will only be modifying or adding more golden queries,
    and not deleting any.
    """
    try:
        for golden_query in request.golden_queries:
            embedding = await get_embedding(text=golden_query.question)
            await set_golden_query(
                db_name=request.db_name,
                question=golden_query.question,
                sql=golden_query.sql,
                question_embedding=embedding
            )
        return {"success": True}
    except Exception as e:
        LOGGER.error(f"Error updating golden queries: {e}")
        LOGGER.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )

@router.post("/integration/delete_golden_queries")
async def delete_golden_queries_route(request: GoldenQueriesDeleteRequest):
    """
    Deletes a list of golden queries for a given db_name.
    """
    try:
        for question in request.questions:
            await delete_golden_query(db_name=request.db_name, question=question)
        return {"success": True}
    except Exception as e:
        LOGGER.error(f"Error deleting golden queries: {e}")
        LOGGER.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )