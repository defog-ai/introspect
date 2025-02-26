from typing import Dict, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from db_models import (
    OracleReports,
)
from db_config import engine
from utils_logging import LOGGER


async def update_status(report_id: int, new_status: str):
    """Update the status of a report."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            await session.execute(
                update(OracleReports)
                .where(OracleReports.report_id == report_id)
                .values(status=new_status)
            )


async def get_report_data(report_id: int, api_key: str) -> Dict:
    """Get report data from the database."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            result = await session.execute(
                select(OracleReports).where(
                    OracleReports.report_id == report_id,
                    OracleReports.db_name == api_key,
                )
            )
            row = result.first()
            if not row:
                return None
            return {
                "report_id": row[0].report_id,
                "report_name": row[0].report_name,
                "status": row[0].status,
                "created_ts": (
                    row[0].created_ts.isoformat() if row[0].created_ts else None
                ),
                "api_key": row[0].db_name,
                "username": row[0].username,
                "inputs": row[0].inputs,
                "outputs": row[0].outputs,
                "feedback": row[0].feedback,
                "comments": row[0].comments,
            }


async def update_report_name(report_id: int, report_name: str):
    """Update the name of a report."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            await session.execute(
                update(OracleReports)
                .where(OracleReports.report_id == report_id)
                .values(report_name=report_name)
            )


