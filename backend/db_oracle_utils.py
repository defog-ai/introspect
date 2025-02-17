from typing import Dict, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from oracle.constants import TaskStage
from db_models import (
    OracleReports,
    OracleAnalyses,
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


async def delete_analysis(api_key: str, analysis_id: str, report_id: int):
    """Delete an analysis from the database."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            await session.execute(
                delete(OracleAnalyses).where(
                    OracleAnalyses.db_name == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id,
                )
            )


async def add_or_update_analysis(
    api_key: str,
    analysis_id: str,
    report_id: int,
    analysis_json: Dict,
    status: str = "pending",
    mdx: str = None,
):
    """Add or update an analysis in the database."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            result = await session.execute(
                select(OracleAnalyses).where(
                    OracleAnalyses.db_name == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id,
                )
            )
            existing_analysis = result.first()

            if existing_analysis:
                await session.execute(
                    update(OracleAnalyses)
                    .where(
                        OracleAnalyses.db_name == api_key,
                        OracleAnalyses.analysis_id == analysis_id,
                        OracleAnalyses.report_id == report_id,
                    )
                    .values(analysis_json=analysis_json, status=status, mdx=mdx)
                )
            else:
                new_analysis = OracleAnalyses(
                    api_key=api_key,
                    analysis_id=analysis_id,
                    report_id=report_id,
                    analysis_json=analysis_json,
                    status=status,
                    mdx=mdx,
                )
                session.add(new_analysis)


async def get_analysis_status(api_key: str, analysis_id: str, report_id: int) -> str:
    """Get the status of an analysis."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            result = await session.execute(
                select(OracleAnalyses.status).where(
                    OracleAnalyses.db_name == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id,
                )
            )
            row = result.first()
            status = row[0] if row else None
            return None, status


async def update_analysis_status(
    api_key: str, analysis_id: str, report_id: int, new_status: str
):
    """Update the status of an analysis."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            result = await session.execute(
                update(OracleAnalyses)
                .where(
                    OracleAnalyses.db_name == api_key,
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id,
                )
                .values(status=new_status)
            )
            if result.rowcount == 0:
                raise Exception("Analysis not found")


async def update_summary_dict(api_key: str, report_id: int, summary_dict: Dict):
    """Update the summary dictionary and optionally the report name."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            report = await session.execute(
                select(OracleReports).where(
                    OracleReports.report_id == report_id,
                    OracleReports.db_name == api_key,
                )
            )
            report = report.first()
            if not report:
                raise Exception("Report not found")

            report = report[0]
            current_outputs = report.outputs or {}

            current_outputs[TaskStage.EXPORT.value]["executive_summary"] = summary_dict

            update_dict = {"outputs": current_outputs}
            if "title" in summary_dict:
                update_dict["report_name"] = summary_dict["title"]

            flag_modified(report, "outputs")
            flag_modified(report, "report_name")
            await session.execute(
                update(OracleReports)
                .where(
                    OracleReports.report_id == report_id,
                    OracleReports.db_name == api_key,
                )
                .values(**update_dict)
            )


async def update_report_name(report_id: int, report_name: str):
    """Update the name of a report."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            await session.execute(
                update(OracleReports)
                .where(OracleReports.report_id == report_id)
                .values(report_name=report_name)
            )


async def get_multiple_analyses(
    analysis_ids: List[str] = [], columns: List[str] = ["analysis_id", "user_question"]
) -> List[Dict]:
    """Get multiple analyses from the database."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            query = select(*[getattr(OracleAnalyses, col) for col in columns])
            if analysis_ids:
                query = query.where(OracleAnalyses.analysis_id.in_(analysis_ids))

            result = await session.execute(query)
            rows = result.all()
            return None, [dict(zip(columns, row)) for row in rows]
