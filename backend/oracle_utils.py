from typing import Dict, List, Tuple
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import (
    OracleReports, OracleAnalyses, OracleSources,
    ImportedTables, OracleGuidelines
)
from db_config import engine
from utils_logging import LOGGER

async def update_status(report_id: int, new_status: str):
    """Update the status of a report."""
    async with AsyncSession(engine) as session:
        try:
            await session.execute(
                update(OracleReports)
                .where(OracleReports.report_id == report_id)
                .values(status=new_status)
            )
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error updating report status: {e}")
            await session.rollback()
            raise

async def get_report_data(report_id: int, api_key: str) -> Dict:
    """Get report data from the database."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(OracleReports)
                .where(
                    OracleReports.report_id == report_id,
                    OracleReports.api_key == api_key
                )
            )
            row = result.first()
            if not row:
                return None
            return {
                "report_id": row[0].report_id,
                "report_name": row[0].report_name,
                "status": row[0].status,
                "created_ts": row[0].created_ts.isoformat() if row[0].created_ts else None,
                "api_key": row[0].api_key,
                "username": row[0].username,
                "inputs": row[0].inputs,
                "outputs": row[0].outputs,
                "feedback": row[0].feedback,
                "comments": row[0].comments
            }
        except Exception as e:
            LOGGER.error(f"Error getting report data: {e}")
            raise

async def delete_analysis(api_key: str, analysis_id: str, report_id: int):
    """Delete an analysis from the database."""
    async with AsyncSession(engine) as session:
        try:
            await session.execute(
                delete(OracleAnalyses).where(
                    OracleAnalyses.api_key == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id
                )
            )
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error deleting analysis: {e}")
            await session.rollback()
            raise

async def add_or_update_analysis(
    api_key: str,
    analysis_id: str,
    report_id: int,
    analysis_json: Dict,
    status: str = "pending",
    mdx: str = None
):
    """Add or update an analysis in the database."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(OracleAnalyses).where(
                    OracleAnalyses.api_key == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id
                )
            )
            existing_analysis = result.first()
            
            if existing_analysis:
                await session.execute(
                    update(OracleAnalyses)
                    .where(
                        OracleAnalyses.api_key == api_key,
                        OracleAnalyses.analysis_id == analysis_id,
                        OracleAnalyses.report_id == report_id
                    )
                    .values(
                        analysis_json=analysis_json,
                        status=status,
                        mdx=mdx
                    )
                )
            else:
                new_analysis = OracleAnalyses(
                    api_key=api_key,
                    analysis_id=analysis_id,
                    report_id=report_id,
                    analysis_json=analysis_json,
                    status=status,
                    mdx=mdx
                )
                session.add(new_analysis)
            
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error adding/updating analysis: {e}")
            await session.rollback()
            raise

async def get_analysis_status(api_key: str, analysis_id: str, report_id: int) -> str:
    """Get the status of an analysis."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(OracleAnalyses.status).where(
                    OracleAnalyses.api_key == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id
                )
            )
            row = result.first()
            return row[0] if row else None
        except Exception as e:
            LOGGER.error(f"Error getting analysis status: {e}")
            raise

async def update_analysis_status(
    api_key: str,
    analysis_id: str,
    report_id: int,
    new_status: str
):
    """Update the status of an analysis."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                update(OracleAnalyses)
                .where(
                    OracleAnalyses.api_key == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id
                )
                .values(status=new_status)
            )
            if result.rowcount == 0:
                raise Exception("Analysis not found")
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error updating analysis status: {e}")
            await session.rollback()
            raise

async def update_summary_dict(api_key: str, report_id: int, summary_dict: Dict):
    """Update the summary dictionary and optionally the report name."""
    async with AsyncSession(engine) as session:
        try:
            report = await session.execute(
                select(OracleReports).where(
                    OracleReports.report_id == report_id,
                    OracleReports.api_key == api_key
                )
            )
            report = report.first()
            if not report:
                raise Exception("Report not found")
            
            report = report[0]
            current_outputs = report.outputs or {}
            current_outputs["summary_dict"] = summary_dict
            
            update_dict = {"outputs": current_outputs}
            if "title" in summary_dict:
                update_dict["report_name"] = summary_dict["title"]
            
            await session.execute(
                update(OracleReports)
                .where(
                    OracleReports.report_id == report_id,
                    OracleReports.api_key == api_key
                )
                .values(**update_dict)
            )
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error updating summary dict: {e}")
            await session.rollback()
            raise

async def update_report_name(report_id: int, report_name: str):
    """Update the name of a report."""
    async with AsyncSession(engine) as session:
        try:
            await session.execute(
                update(OracleReports)
                .where(OracleReports.report_id == report_id)
                .values(report_name=report_name)
            )
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error updating report name: {e}")
            await session.rollback()
            raise
