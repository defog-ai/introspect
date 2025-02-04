from datetime import datetime
import uuid
from typing import Dict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import Analyses
from db_config import engine
from utils_logging import LOGGER
from auth_utils import validate_user

async def initialise_analysis(
    user_question, token, api_key, custom_id=None, other_initialisation_details={}
):
    username = await validate_user(token, get_username=True)
    if not username:
        return "Invalid token.", None

    err = None
    timestamp = datetime.now()
    new_analysis_data = None

    try:
        """Create a new analyis in the defog_analyses table"""
        async with engine.begin() as conn:
            if not custom_id or custom_id == "":
                analysis_id = str(uuid.uuid4())
            else:
                analysis_id = custom_id
            LOGGER.info("Creating new analyis with uuid: ", analysis_id)
            new_analysis_data = {
                "user_question": user_question,
                "timestamp": timestamp,
                "analysis_id": analysis_id,
                "api_key": api_key,
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
                select(Analyses.assignment_understanding)
                .where(Analyses.analysis_id == analysis_id)
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
    replace: bool = False,
    overwrite_key: str = None
) -> Dict:
    """Update analysis data in the database."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(Analyses).where(Analyses.analysis_id == analysis_id)
            )
            analysis = result.first()
            if not analysis:
                return None
            
            analysis = analysis[0]
            if request_type == "clarify":
                if replace:
                    analysis.clarify = new_data
                else:
                    current_data = analysis.clarify or []
                    current_data.append(new_data)
                    analysis.clarify = current_data
            
            elif request_type == "gen_steps":
                if replace:
                    analysis.gen_steps = new_data
                else:
                    current_data = analysis.gen_steps or []
                    current_data.append(new_data)
                    analysis.gen_steps = current_data
            
            elif overwrite_key:
                setattr(analysis, overwrite_key, new_data)
            
            await session.commit()
            return analysis_data_from_row(analysis)
        except Exception as e:
            LOGGER.error(f"Error updating analysis data: {e}")
            await session.rollback()
            raise

def analysis_data_from_row(row):
    clarify = None if row.clarify is None else row.clarify
    gen_steps = None if row.gen_steps is None else row.gen_steps
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