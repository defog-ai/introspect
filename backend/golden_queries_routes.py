from auth_utils import validate_user_request
from db_models import GoldenQueries
from db_utils import engine
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from request_models import GoldenQueriesDeleteRequest, GoldenQueriesUpdateRequest, UserRequest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
import traceback
from utils_logging import LOGGER

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Golden Queries"],
)


@router.post("/integration/get_golden_queries")
async def get_golden_queries_route(request: UserRequest):
    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = await session.execute(
                    select(GoldenQueries.question, GoldenQueries.sql).where(
                        GoldenQueries.db_name == request.db_name
                    )
                )
                result = stmt.all()
                golden_queries = [{"question": r[0], "sql": r[1]} for r in result]
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
        async with AsyncSession(engine) as session:
            async with session.begin():
                for golden_query in request.golden_queries:
                    # check if golden query already exists under the same db_name
                    current_golden_query = await session.execute(
                        select(GoldenQueries).where(
                            GoldenQueries.db_name == request.db_name,
                            GoldenQueries.question == golden_query.question
                        )
                    )
                    existing_golden_query = current_golden_query.scalar_one_or_none()
                    if existing_golden_query:
                        # update existing golden query
                        existing_golden_query.sql = golden_query.sql
                    else:
                        session.add(
                            GoldenQueries(
                                db_name=request.db_name,
                                question=golden_query.question,
                                sql=golden_query.sql,
                            )
                        )
                await session.commit()
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
        async with AsyncSession(engine) as session:
            async with session.begin():
                for question in request.questions:
                    await session.execute(delete(GoldenQueries).where(GoldenQueries.question == question))
                await session.commit()
                return {"success": True}
    except Exception as e:
        LOGGER.error(f"Error deleting golden queries: {e}")
        LOGGER.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )