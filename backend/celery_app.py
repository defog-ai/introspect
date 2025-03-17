"""
Celery application configuration for background tasks
"""
import os
from celery import Celery
from utils_logging import LOGGER

# Configure Celery with Redis broker and backend
redis_host = os.environ.get("REDIS_HOST", "agents-redis")
redis_port = os.environ.get("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/0"

# Initialize Celery app
celery_app = Celery(
    "defog_tasks",
    broker=redis_url,
    backend=redis_url,
)

# Import tasks here to avoid circular imports
celery_app.conf.update(
    imports=["celery_tasks.pdf_tasks"],
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    task_track_started=True,
    worker_concurrency=2,  # Adjust based on server capacity
    task_time_limit=1800,  # 30 minutes max per task
    broker_connection_retry_on_startup=True
)

# Use Celery built-in signals
from celery.signals import task_prerun, task_success, task_failure

@task_prerun.connect
def task_prerun_handler(task_id=None, task=None, *args, **kwargs):
    LOGGER.info(f"Starting task {task.name}[{task_id}]")

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    LOGGER.info(f"Task {sender.name} completed successfully")

@task_failure.connect
def task_failure_handler(task_id=None, exception=None, traceback=None, 
                         sender=None, *args, **kwargs):
    LOGGER.error(f"Task {sender.name}[{task_id}] failed: {exception}")