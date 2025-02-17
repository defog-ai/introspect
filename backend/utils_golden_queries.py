########################################
### Instructions Related Functions Below ###
########################################

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import GoldenQueries
from db_config import engine
from pydantic import BaseModel, Field
from typing import List


class GoldenQuery(BaseModel):
    db_name: str = Field(..., description="The name of the database")
    question: str = Field(..., description="The question to generate SQL for")
    sql: str = Field(..., description="The query itself")


async def get_all_golden_queries(db_name: str) -> list[dict[str, str]]:
    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = await session.execute(
                select(GoldenQueries.question, GoldenQueries.sql).where(
                    GoldenQueries.db_name == db_name
                )
            )
            result = stmt.all()
            golden_queries = [{"question": r[0], "sql": r[1]} for r in result]
            return golden_queries


async def get_closest_golden_queries(
    db_name: str, question_embedding: List[float], num_queries: int = 4
) -> List[GoldenQuery]:
    async with AsyncSession(engine) as session:
        async with session.begin():
            result = await session.execute(
                select(GoldenQueries.question, GoldenQueries.sql)
                .where(GoldenQueries.db_name == db_name)
                .order_by(GoldenQueries.embedding.cosine_distance(question_embedding))
                .limit(num_queries)
            )
            closest_queries = []
            for row in result.all():
                closest_queries.append(
                    GoldenQuery(db_name=db_name, question=row[0], sql=row[1])
                )
            return closest_queries


async def set_golden_query(
    db_name: str, question: str, sql: str, question_embedding: List[float]
) -> None:
    async with AsyncSession(engine) as session:
        async with session.begin():
            new_query = await session.execute(
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
                    embedding=question_embedding,
                )
                session.add(new_query)
            else:
                new_query.sql = sql
                new_query.embedding = question_embedding
            return

async def delete_golden_query(db_name: str, question: str) -> None:
    async with AsyncSession(engine) as session:
        async with session.begin():
            await session.execute(
                delete(GoldenQueries)
                .where(GoldenQueries.db_name == db_name)
                .where(GoldenQueries.question == question)
            )
    return