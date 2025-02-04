from datetime import datetime
import uuid
from typing import Dict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import Analyses
from db_config import engine
from utils_logging import LOGGER

async def initialise_analysis(
    user_question: str,
    token: str,
    api_key: str,
    custom_id: str = None,
    other_initialisation_details: Dict = {}
) -> Dict:
    """Initialize a new analysis in the database."""
    from auth_utils import validate_user
    
    username = validate_user(token, get_username=True)
    analysis_id = custom_id if custom_id else str(uuid.uuid4())
    
    analysis = {
        "analysis_id": analysis_id,
        "api_key": api_key,
        "username": username,
        "timestamp": datetime.utcnow(),
        "user_question": user_question,
        **other_initialisation_details
    }
    
    async with AsyncSession(engine) as session:
        try:
            session.add(Analyses(**analysis))
            await session.commit()
            return None, analysis
        except Exception as e:
            LOGGER.error(f"Error initialising analysis: {e}")
            await session.rollback()
            return str(e), None

async def get_analysis_data(analysis_id: str) -> Dict:
    """Get analysis data from the database."""
    async with AsyncSession(engine) as session:
        try:
            result = await session.execute(
                select(Analyses).where(Analyses.analysis_id == analysis_id)
            )
            row = result.first()
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

def analysis_data_from_row(row) -> Dict:
    """Convert an analysis database row to a dictionary."""
    return {
        "analysis_id": row.analysis_id,
        "api_key": row.api_key,
        "email": row.email,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "clarify": row.clarify,
        "assignment_understanding": row.assignment_understanding,
        "user_question": row.user_question,
        "gen_steps": row.gen_steps,
        "follow_up_analyses": row.follow_up_analyses,
        "parent_analyses": row.parent_analyses,
        "is_root_analysis": row.is_root_analysis,
        "root_analysis_id": row.root_analysis_id,
        "direct_parent_id": row.direct_parent_id,
        "username": row.username
    }
