import traceback
import uuid
from datetime import datetime
from typing import Dict, Tuple

from sqlalchemy.orm.attributes import flag_modified

from auth_utils import validate_user
from agent_models import AnalysisData
from db_config import engine
from db_models import Analyses
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from utils_logging import LOGGER


async def initialise_analysis(
    user_question, token, db_name, custom_id=None, other_initialisation_details={}
):
    user = await validate_user(token)
    if not user:
        return "Invalid token.", None

    err = None
    timestamp = datetime.now()
    new_analysis = None

    try:
        """Create a new analyis in the analyses table"""
        async with AsyncSession(engine) as session:
            async with session.begin():
                if not custom_id or custom_id == "":
                    analysis_id = str(uuid.uuid4())
                else:
                    analysis_id = custom_id
                LOGGER.info("Creating new analyis with uuid: {analysis_id}")

                new_analysis = {
                    "analysis_id": analysis_id,
                    "timestamp": timestamp,
                    "db_name": db_name,
                    "data": {},
                }

                data: AnalysisData = AnalysisData(
                    analysis_id=analysis_id,
                    db_name=db_name,
                    user_question=user_question,
                )

                new_analysis["data"] = data.model_dump()

                if (
                    other_initialisation_details is not None
                    and type(other_initialisation_details) is dict
                ):
                    new_analysis.update(other_initialisation_details)

                await session.execute(insert(Analyses).values(new_analysis))

                # if other data has parent_analyses, insert analysis_id into the follow_up_analyses column, which is an array, of all the parent analyses
                if (
                    other_initialisation_details is not None
                    and type(other_initialisation_details) is dict
                    and other_initialisation_details.get("parent_analyses") is not None
                ):
                    for parent_analysis_id in other_initialisation_details.get(
                        "parent_analyses"
                    ):
                        # get the parent analysis
                        parent_analysis = await session.execute(
                            select(Analyses).where(
                                Analyses.analysis_id == parent_analysis_id
                            )
                        )

                        parent_analysis = parent_analysis.fetchone()
                        if parent_analysis is not None:
                            parent_analysis = parent_analysis._mapping
                            # get the follow_up_analyses array
                            follow_up_analyses = (
                                parent_analysis.get("follow_up_analyses") or []
                            )
                            # add the analysis_id to the array
                            follow_up_analyses.append(analysis_id)
                            # update the row
                            await session.execute(
                                update(Analyses)
                                .where(Analyses.analysis_id == parent_analysis_id)
                                .values(follow_up_analyses=follow_up_analyses)
                            )
                        else:
                            print(
                                "Could not find parent analysis with id: ",
                                parent_analysis_id,
                            )

    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not create a new analysis."
        new_analysis = None
    finally:
        return err, analysis_dict_from_row(new_analysis)


async def get_analysis(analysis_id: str) -> Tuple[str, Dict]:
    """Get an analysis from the database."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(Analyses).where(Analyses.analysis_id == analysis_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return "Analysis not found", None
            result = row
            return None, result
        except Exception as e:
            LOGGER.error(f"Error getting analysis data: {e}")
            return str(e), None


async def get_assignment_understanding(analysis_id: str) -> Tuple[str, Dict]:
    """Get the assignment understanding for an analysis."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(Analyses.assignment_understanding).where(
                    Analyses.analysis_id == analysis_id
                )
            )
            row = result.first()
            result = row[0] if row else None
            return None, result
        except Exception as e:
            LOGGER.error(f"Error getting assignment understanding: {e}")
            return str(e), None


async def update_assignment_understanding(analysis_id: str, understanding: Dict):
    """Update the assignment understanding for an analysis."""
    async with AsyncSession(engine) as session:
        try:
            await session.execute(
                update(Analyses)
                .where(Analyses.analysis_id == analysis_id)
                .values(assignment_understanding=understanding)
            )
            await session.commit()
        except Exception as e:
            LOGGER.error(f"Error updating assignment understanding: {e}")
            await session.rollback()
            raise


async def update_analysis_data(
    analysis_id: str,
    new_data: Dict = None,
) -> Tuple[str | None, Dict | None]:
    """Update analysis data in the database."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            try:
                result = await session.execute(
                    select(Analyses).where(Analyses.analysis_id == analysis_id)
                )
                analysis = result.scalar_one_or_none()
                if not analysis:
                    return "Analysis not found", None
                analysis.data = new_data
                flag_modified(analysis, "data")

                row = await session.execute(
                    update(Analyses)
                    .where(Analyses.analysis_id == analysis_id)
                    .values(data=new_data)
                    .returning(Analyses)
                )

                row = row.scalar_one_or_none()
                if not row:
                    raise Exception("Analysis not found")

                return None, analysis_dict_from_row(row)

            except Exception as e:
                LOGGER.error(f"Error updating analysis data: {e}")
                return str(e), None


def analysis_dict_from_row(row: Analyses):
    analysis_id = row.get("analysis_id", None)
    user_question = row.get("user_question", None)
    timestamp = row.get("timestamp", None)
    data = row.get("data", None)
    db_name = row.get("db_name", None)
    follow_up_analyses = row.get("follow_up_analyses", None)
    parent_analyses = row.get("parent_analyses", None)
    is_root_analysis = row.get("is_root_analysis", None)
    root_analysis_id = row.get("root_analysis_id", None)
    direct_parent_id = row.get("direct_parent_id", None)

    return {
        "analysis_id": analysis_id,
        "user_question": user_question,
        "timestamp": str(timestamp),
        "data": data,
        "db_name": db_name,
        "follow_up_analyses": follow_up_analyses,
        "parent_analyses": parent_analyses,
        "is_root_analysis": is_root_analysis,
        "root_analysis_id": root_analysis_id,
        "direct_parent_id": direct_parent_id,
    }
