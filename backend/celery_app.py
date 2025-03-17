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

# Register signal handlers using decorator functions
@celery_app.on_after_configure.connect
def setup_signals(sender, **kwargs):
    # Register signal handlers
    sender.on_after_task_publish.connect(task_sent_handler)
    sender.on_task_prerun.connect(task_prerun_handler)
    sender.on_task_success.connect(task_success_handler)
    sender.on_task_failure.connect(task_failure_handler)

def task_sent_handler(sender=None, headers=None, body=None, **kwargs):
    info = headers if 'task' in headers else body
    LOGGER.info(f"Task sent: {info.get('task', 'Unknown')}")

def task_prerun_handler(task_id, task, *args, **kwargs):
    LOGGER.info(f"Starting task {task.name}[{task_id}]")

def task_success_handler(sender=None, result=None, **kwargs):
    LOGGER.info(f"Task {sender.name} completed with result: {result}")

def task_failure_handler(task_id, exception, traceback, einfo, *args, **kwargs):
    LOGGER.error(f"Task {task_id} failed: {exception}")