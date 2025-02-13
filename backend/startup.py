import os
from contextlib import asynccontextmanager
from typing import Union

from auth_utils import get_hashed_password, login_user
from db_config import ORACLE_ENABLED
from db_models import Base, ImportedTables, Users
from fastapi import FastAPI
from sqlalchemy import Engine, insert
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


async def init_db(
    engine: Union[AsyncEngine, Engine], imported_tables_engine: Engine | None
):
    """
    Initialize database tables
    Args:
        engine: AsyncEngine for main database
        imported_tables_engine: AsyncEngine for imported tables database, None if not using imported tables
    """
    try:
        if isinstance(engine, AsyncEngine):
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            Base.metadata.create_all(engine)

        if ORACLE_ENABLED and imported_tables_engine:
            try:
                ImportedTablesBase = automap_base()
                ImportedTablesBase.prepare(autoload_with=imported_tables_engine)
                ImportedTablesBase.classes.imported_tables = ImportedTables
                with imported_tables_engine.begin() as conn:
                    ImportedTablesBase.metadata.create_all(conn)
            except Exception as e:
                LOGGER.error(f"Error creating imported tables: {str(e)}")
                raise e

        LOGGER.info("Database tables created successfully")
    except Exception as e:
        LOGGER.error(f"Error initializing database: {str(e)}")
        raise


async def create_admin_user():
    """Create admin user if it doesn't exist"""
    from db_config import engine

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
                        token=get_hashed_password(admin_username, admin_password)
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
        from db_config import engine, imported_tables_engine

        LOGGER.info("Running startup events...")

        # Initialize database tables
        await init_db(engine, imported_tables_engine)
        LOGGER.info("Database tables initialized")

        # Create admin user if doesn't exist
        await create_admin_user()
        LOGGER.info("Admin user check completed")

        if ORACLE_ENABLED:
            from oracle.setup import setup_dir

            # check if the oracle directory structure exists and create if not
            setup_dir(os.getcwd())
            LOGGER.info("Oracle directory structure checked")

        LOGGER.info("All startup events completed successfully")

        yield

        LOGGER.info("Shutting down...")
    except Exception as e:
        LOGGER.error(f"Startup failed: {str(e)}")
        raise
