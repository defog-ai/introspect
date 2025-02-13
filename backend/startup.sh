#!/bin/sh

# print PID of the current process
echo "Current PID: $$"

echo "Starting FastAPI server"
echo "PROD: $PROD"

# Start the FastAPI server
if [ "$PROD" = "no" ]; then
  echo "Running in development mode"
  python3 -m hypercorn main:app -b 0.0.0.0:1235 --reload &
else
  echo "Running in production mode"
  python3 -m hypercorn main:app -b 0.0.0.0:1235 &
fi

FASTAPI_PID=$!

# Start celery worker
nohup celery -A oracle.celery_app.celery_app worker --loglevel=info --logfile=/dev/stdout &

CELERY_PID=$!

# Forward signals to the whole process group, exiting after the processes are killed
trap 'echo "[start_docker.sh] Received signal. Shutting down..."; kill -TERM $FASTAPI_PID $CELERY_PID; wait $FASTAPI_PID $CELERY_PID; exit' TERM INT

# Wait for all processes to finish
wait $FASTAPI_PID $CELERY_PID
