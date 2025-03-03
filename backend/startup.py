import os
from contextlib import asynccontextmanager

from db_models import Base, Users
from fastapi import FastAPI
from sqlalchemy import Engine, insert, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.automap import automap_base
from utils_logging import LOGGER

################################################################################
# This file is used to consolidate all the startup and shutdown events into a
# single function. We package them all within a single lifespan function so that
# we can ensure that all the startup events are completed successfully before
# the server starts accepting requests, and that all the shutdown events are
# completed successfully before the server shuts down.
################################################################################


async def init_db(engine: AsyncEngine):
    """
    Initialize database tables
    Args:
        engine: AsyncEngine for main database
    """
    try:
        async with engine.begin() as conn:
            # need to create the vector extension first before creating tables
            # that contain vector columns
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.run_sync(Base.metadata.create_all)

        LOGGER.info("Database tables created successfully")
    except Exception as e:
        LOGGER.error(f"Error initializing database: {str(e)}")
        raise


async def create_admin_user():
    """Create admin user if it doesn't exist"""
    from db_config import engine

    # auth_utils imported inside here to prevent a race condition because of multiple calls to get_db_engine
    from auth_utils import get_hashed_password, login_user

    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin")

    try:
        # Check if admin user exists
        token = await login_user(admin_username, admin_password)
        if not token:
            LOGGER.info("Creating admin user")
            async with engine.begin() as conn:
                await conn.execute(
                    insert(Users).values(
                        username=admin_username,
                        hashed_password=get_hashed_password(
                            admin_username, admin_password
                        ),
                        token=get_hashed_password(admin_username, admin_password),
                    )
                )
            LOGGER.info("Admin user created successfully")
        else:
            LOGGER.info("Admin user already exists")
    except Exception as e:
        LOGGER.error(f"Error creating admin user: {str(e)}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and admin user on startup"""
    try:
        # Run validation on current llm sdk version to ensure models used are supported
        from db_config import engine

        LOGGER.info("Running startup events...")

        # Initialize database tables
        await init_db(engine)
        LOGGER.info("Database tables initialized")

        # Create admin user if doesn't exist
        await create_admin_user()
        LOGGER.info("Admin user check completed")

        LOGGER.info("All startup events completed successfully")

        yield

        LOGGER.info("Shutting down...")
    except Exception as e:
        LOGGER.error(f"Startup failed: {str(e)}")
        raise
