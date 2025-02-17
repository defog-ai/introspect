import traceback
import uuid
from datetime import datetime
from typing import Dict

from auth_utils import validate_user
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

    username = user.username

    err = None
    timestamp = datetime.now()
    new_analysis_data = None

    try:
        """Create a new analyis in the analyses table"""
        async with engine.begin() as conn:
            if not custom_id or custom_id == "":
                analysis_id = str(uuid.uuid4())
            else:
                analysis_id = custom_id
            LOGGER.info("Creating new analyis with uuid: {analysis_id}")
            new_analysis_data = {
                "user_question": user_question,
                "timestamp": timestamp,
                "analysis_id": analysis_id,
                "db_name": db_name,
                "username": username,
            }
            if (
                other_initialisation_details is not None
                and type(other_initialisation_details) is dict
            ):
                new_analysis_data.update(other_initialisation_details)

            await conn.execute(insert(Analyses).values(new_analysis_data))
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
                    parent_analysis = await conn.execute(
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
                        await conn.execute(
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
        new_analysis_data = None
    finally:
        return err, new_analysis_data


async def get_analysis_data(analysis_id: str) -> Dict:
    """Get analysis data from the database."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(Analyses).where(Analyses.analysis_id == analysis_id)
            )
            row = result.fetchone()
            if not row:
                return "Analysis not found", None
            result = analysis_data_from_row(row[0])
            return None, result
        except Exception as e:
            LOGGER.error(f"Error getting analysis data: {e}")
            return str(e), None


async def get_assignment_understanding(analysis_id: str) -> Dict:
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
    request_type: str = None,
    new_data: Dict = None,
) -> Dict:
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
                if request_type == "clarify":
                    analysis.clarify = new_data

                elif request_type == "gen_steps":
                    analysis.gen_steps = new_data

                data = analysis_data_from_row(analysis)
                return data
            except Exception as e:
                LOGGER.error(f"Error updating analysis data: {e}")
                raise


def analysis_data_from_row(row):
    clarify = row.clarify
    gen_steps = row.gen_steps
    parent_analyses = row.parent_analyses or []
    follow_up_analyses = row.follow_up_analyses or []
    direct_parent_id = row.direct_parent_id or None

    # send only the ones that are not none.
    rpt = {
        "user_question": row.user_question,
        "analysis_id": row.analysis_id,
        "timestamp": row.timestamp,
        "parent_analyses": parent_analyses,
        "follow_up_analyses": follow_up_analyses,
        "direct_parent_id": direct_parent_id,
    }

    if clarify is not None:
        rpt["clarify"] = {
            "success": True,
            "clarification_questions": clarify,
        }

    if gen_steps is not None:
        rpt["gen_steps"] = {
            "success": True,
            "steps": gen_steps,
        }

    return rpt
