#!/bin/sh

# print PID of the current process
echo "Current PID: $$"

echo "Starting Celery worker for background tasks"
# Start the Celery worker in the background
python -m celery -A celery_worker.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!
echo "Celery worker started with PID: $CELERY_PID"

echo "Starting FastAPI server"
echo "PROD: $PROD"

# Start the FastAPI server
if [ "$PROD" = "no" ]; then
  echo "Running in development mode"
  hypercorn main:app --workers 4 -b 0.0.0.0:1235 --log-level warning --worker-class uvloop --reload &
else
  echo "Running in production mode"
  hypercorn main:app --workers 4 -b 0.0.0.0:1235 --log-level warning --worker-class uvloop &
fi

FASTAPI_PID=$!

# Forward signals to the whole process group, exiting after the processes are killed
trap 'echo "[startup.sh] Received signal. Shutting down..."; kill -TERM $FASTAPI_PID; kill -TERM $CELERY_PID; wait $FASTAPI_PID; wait $CELERY_PID; echo "All processes terminated"; exit' TERM INT

# Wait for all processes to finish
echo "Waiting for server processes..."
wait $FASTAPI_PID $CELERY_PID
