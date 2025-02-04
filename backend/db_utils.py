"""Database credential utility functions."""
from typing import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db_config import engine
from db_models import DbCreds
from utils_logging import LOGGER

async def get_db_type_creds(api_key: str) -> Dict:
    """Get database credentials for a given API key."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(DbCreds).where(DbCreds.api_key == api_key)
            )
            row = result.first()
            if not row:
                return None
            return {
                "db_type": row[0].db_type,
                "db_creds": row[0].db_creds
            }
        except Exception as e:
            LOGGER.error(f"Error getting db type creds: {e}")
            raise

async def update_db_type_creds(api_key: str, db_type: str, db_creds: Dict):
    """Update database credentials for a given API key."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(DbCreds).where(DbCreds.api_key == api_key)
            )
            db_creds_row = result.first()
            
            if db_creds_row:
                db_creds_row = db_creds_row[0]
                db_creds_row.db_type = db_type
                db_creds_row.db_creds = db_creds
            else:
                session.add(
                    DbCreds(
                        api_key=api_key,
                        db_type=db_type,
                        db_creds=db_creds
                    )
                )
            
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error updating db type creds: {e}")
            await session.rollback()
            raise
