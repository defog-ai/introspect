from auth_utils import validate_user_request
from db_models import GoldenQueries
from db_utils import engine
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from request_models import GoldenQueriesUpdateRequest, UserRequest
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
                return {"golden_queries": [{"question": r[0], "sql": r[1]} for r in result]}
    except Exception as e:
        LOGGER.error(f"Error getting golden queries: {e}")
        LOGGER.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/integration/update_golden_queries")
async def update_golden_queries_route(request: GoldenQueriesUpdateRequest):
    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                # delete all existing golden queries
                await session.execute(delete(GoldenQueries).where(GoldenQueries.db_name == request.db_name))
                # add new golden queries
                for golden_query in request.golden_queries:
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
