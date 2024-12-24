import os
import redis
from utils_logging import LOGGER

REDIS_HOST = os.getenv("REDIS_INTERNAL_HOST", "agents-redis")
REDIS_PORT = int(os.getenv("REDIS_INTERNAL_PORT", 6379))

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,  # Use the same db as Celery
    decode_responses=True,  # Automatically decode responses to strings
)

def store_analysis_task_id(analysis_id: str, task_id: str) -> None:
    """Store the Celery task ID for a given analysis ID."""
    try:
        redis_client.set(f"analysis_task:{analysis_id}", task_id)
    except Exception as e:
        LOGGER.error(f"Error storing task ID for analysis {analysis_id}: {str(e)}")

def get_analysis_task_id(analysis_id: str) -> str:
    """Get the Celery task ID for a given analysis ID."""
    try:
        return redis_client.get(f"analysis_task:{analysis_id}")
    except Exception as e:
        LOGGER.error(f"Error getting task ID for analysis {analysis_id}: {str(e)}")
        return None

def delete_analysis_task_id(analysis_id: str) -> None:
    """Delete the Celery task ID for a given analysis ID."""
    try:
        redis_client.delete(f"analysis_task:{analysis_id}")
    except Exception as e:
        LOGGER.error(f"Error deleting task ID for analysis {analysis_id}: {str(e)}")
