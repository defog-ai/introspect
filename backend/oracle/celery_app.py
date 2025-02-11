import os
from celery import Celery

from utils_logging import LOGGER
from concurrent.futures import ThreadPoolExecutor
# Initialize Celery with redis backend
REDIS_HOST = os.getenv("REDIS_INTERNAL_HOST", "agents-redis")
REDIS_PORT = os.getenv("REDIS_INTERNAL_PORT", 6379)
celery_app = Celery(
    "tasks",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
    include=["oracle.core"],
)

# Create a thread pool executor for async tasks
celery_async_executors = ThreadPoolExecutor(max_workers=4)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

LOGGER.info(f"Initialized Celery app:\n{celery_app}")
