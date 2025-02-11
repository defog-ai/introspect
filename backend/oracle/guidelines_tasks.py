import json
import asyncio
from typing import Dict, Any
import os
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db_config import engine
from db_models import OracleGuidelines
from oracle.celery_app import celery_app, celery_async_executors, LOGGER
from generic_utils import make_request

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


@celery_app.task(name="populate_default_guidelines_task")
def populate_default_guidelines_task(api_key: str):
    """Celery task to populate default guidelines for an API key if they don't exist."""

    async def _populate_guidelines():
        try:
            async with AsyncSession(engine) as session:
                # Check if guidelines exist
                stmt = select(OracleGuidelines).where(
                    OracleGuidelines.api_key == api_key
                )
                result = await session.execute(stmt)
                existing = result.fetchone()

                if existing and not existing[0].clarification_guidelines:
                    LOGGER.info(f"Generating guidelines for api_key {api_key}")

                    # Make request to generate guidelines
                    response = await make_request(
                        f"{DEFOG_BASE_URL}/generate_clarification_guidelines",
                        data={"api_key": api_key},
                    )

                    if (
                        not isinstance(response, dict)
                        or "clarification_guidelines" not in response
                    ):
                        raise Exception(f"Failed to generate guidelines: {response}")

                    guidelines = response["clarification_guidelines"]

                    # Update the database with the generated guidelines
                    await session.execute(
                        update(OracleGuidelines)
                        .values(
                            clarification_guidelines=guidelines,
                        )
                        .where(OracleGuidelines.api_key == api_key)
                    )
                    await session.commit()
                    LOGGER.info(
                        f"Populated AI-generated guidelines for api_key {api_key}"
                    )
                else:
                    LOGGER.info(
                        f"Skipping default guidelines population for api_key {api_key} as they already exist"
                    )
        except Exception as e:
            LOGGER.error(f"Error populating default guidelines: {str(e)}")
            raise

    with celery_async_executors:
        loop = asyncio.get_event_loop()
        task = loop.create_task(_populate_guidelines())
        return loop.run_until_complete(task)
