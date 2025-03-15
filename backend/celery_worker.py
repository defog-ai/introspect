"""
Celery worker script for starting the Celery worker.

Run this with:
celery -A celery_worker.celery_app worker --loglevel=info
"""

from celery_app import celery_app

# Import tasks to register them with Celery
import celery_tasks.pdf_tasks

if __name__ == '__main__':
    celery_app.start()