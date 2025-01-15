import logging
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.exc import SQLAlchemyError

from db_utils import engine, get_db_type_creds

LOGGER = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def test_engine():
    """Fixture to get database engine and verify it's async"""
    if not isinstance(engine, AsyncEngine):
        pytest.fail("Database engine is not async. Expected AsyncEngine instance.")
    yield engine
    await engine.dispose()

# log pool status
@pytest.mark.asyncio
async def test_pool_status(test_engine: AsyncEngine):
    try:
        LOGGER.info("Connection pool status: %s", test_engine.pool.status())
    except AttributeError as e:
        pytest.fail("Connection does not support async operations. Are you using create_async_engine?")
    except SQLAlchemyError as e:
        pytest.fail(f"Database connection failed: {str(e)}")

@pytest.mark.asyncio
async def test_async_connection(test_engine: AsyncEngine):
    """Test that we can make async database connections"""
    try:
        async with test_engine.begin() as session:
            result = await session.execute(select(1))
            value = result.scalar()
            assert value == 1
    except AttributeError as e:
        pytest.fail("Connection does not support async operations. Are you using create_async_engine?")
    except SQLAlchemyError as e:
        pytest.fail(f"Database connection failed: {str(e)}")

@pytest.mark.asyncio
async def test_api_key_names(test_engine: AsyncEngine):
    try:
        db_type, db_creds = await get_db_type_creds("test_restaurant")
        LOGGER.info(f"Database type: {db_type}")
        LOGGER.info(f"Database credentials: {db_creds}")
    except AttributeError as e:
        pytest.fail("Connection does not support async operations. Are you using create_async_engine?")
    except SQLAlchemyError as e:
        pytest.fail(f"Database connection failed: {str(e)}")