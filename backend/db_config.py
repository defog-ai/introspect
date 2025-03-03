import os
import contextlib
from typing import AsyncGenerator

import redis
import psycopg2
import pyodbc
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from utils_logging import LOGGER

REDIS_HOST = os.getenv("REDIS_INTERNAL_HOST", "agents-redis")
REDIS_PORT = os.getenv("REDIS_INTERNAL_PORT", 6379)
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)

INTERNAL_DB = os.environ.get("INTERNAL_DB", None)

def get_db_engine() -> tuple[AsyncEngine, Engine | None, Engine | None]:
    """
    Returns a tuple of the 
    - async engine for querying the user's database,
    - engine for querying the imported tables database, and
    - engine for querying the temp tables database.
    """
    if INTERNAL_DB == "sqlite":
        print("using sqlite as our internal db")
        connection_uri = "sqlite:///defog_local.db"
        engine = create_async_engine(connection_uri, connect_args={"timeout": 3})
        return engine

    elif INTERNAL_DB == "postgres":
        db_creds = {
            "user": os.environ.get("DBUSER", "postgres"),
            "password": os.environ.get("DBPASSWORD", "postgres"),
            "host": os.environ.get("DBHOST", "agents-postgres"),
            "port": os.environ.get("DBPORT", "5432"),
            "database": os.environ.get("DATABASE", "postgres"),
        }

        print("using postgres as our internal db")
        connection_uri = f"postgresql+asyncpg://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
        engine = create_async_engine(connection_uri, pool_size=30)

        return engine

    elif INTERNAL_DB == "sqlserver":
        db_creds = {
            "user": os.environ.get("DBUSER", "sa"),
            "password": os.environ.get("DBPASSWORD", "Password1"),
            "host": os.environ.get("DBHOST", "localhost"),
            "database": os.environ.get("DATABASE", "defog"),
            "port": os.environ.get("DBPORT", "1433"),
        }

        connection_uri = f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}?driver=ODBC+Driver+18+for+SQL+Server"
        engine = create_async_engine(connection_uri)

        return engine


engine = get_db_engine()


@contextlib.asynccontextmanager
async def get_defog_internal_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Returns an async session for interacting with the defog internal database.
    This should be used with an async context manager:
    
    async with get_defog_internal_session() as session:
        # Use the session
        result = await session.execute(...)
    """
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
