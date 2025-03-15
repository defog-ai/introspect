"""
Celery application configuration for background tasks
"""
import os
from celery import Celery
from utils_logging import LOGGER

# Configure Celery with Redis broker and backend
redis_host = os.environ.get("REDIS_HOST", "redis")
redis_port = os.environ.get("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/0"

celery_app = Celery(
    "defog_tasks",
    broker=redis_url,
    backend=redis_url,
    include=["celery_tasks.pdf_tasks"]
)

# Optional: Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    task_track_started=True,
    worker_concurrency=4,  # Adjust based on server capacity
    task_time_limit=1800,  # 30 minutes max per task
    broker_connection_retry_on_startup=True
)

# Optional: Register signals for logging/monitoring
@celery_app.task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    LOGGER.info(f"Starting task {task.name}[{task_id}]")

@celery_app.task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, *args, **kwargs):
    LOGGER.info(f"Task {task.name}[{task_id}] finished with state: {state}")

@celery_app.task_failure.connect
def task_failure_handler(task_id, exception, traceback, einfo, *args, **kwargs):
    LOGGER.error(f"Task {task_id} failed: {exception}")