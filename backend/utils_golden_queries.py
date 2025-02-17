########################################
### Instructions Related Functions Below ###
########################################

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import GoldenQueries
from db_config import engine
from pydantic import BaseModel, Field
from typing import List

class GoldenQuery(BaseModel):
    db_name: str = Field(..., description="The name of the database")
    question: str = Field(..., description="The question to generate SQL for")
    sql: str = Field(..., description="The query itself")

async def get_all_golden_queries(db_name: str) -> List[GoldenQuery]:
    async with engine.begin() as conn:
        result = await conn.execute(select(GoldenQueries).where(GoldenQueries.db_name == db_name))
        return result.scalars().all()

async def get_closest_golden_queries(db_name: str, question_embedding: List[float]) -> List[GoldenQuery]:
    async with engine.begin() as conn:
        result = await conn.execute(
            select(GoldenQueries)
            .where(GoldenQueries.db_name == db_name)
            .order_by(
                GoldenQueries.embedding.cosine_distance(question_embedding)
            )
            .limit(5)
        )
        return result.scalars().all()

async def set_golden_query(
    db_name: str,
    question: str,
    sql: str,
    question_embedding: List[float]
) -> None:
    async with AsyncSession(engine) as session:
        async with engine.begin() as conn:
            new_query = await conn.execute(
                select(GoldenQueries)
                .where(GoldenQueries.db_name == db_name)
                .where(GoldenQueries.question == question)
            ).scalar_one_or_none()
            
            if new_query is None:
                # add new query to db
                new_query = GoldenQueries(
                    db_name=db_name,
                    question=question,
                    sql=sql,
                    embedding=question_embedding
                )
                conn.add(new_query)
                await conn.commit()
                await conn.refresh(new_query)
            else:
                new_query.sql = sql
                new_query.embedding = question_embedding
            return