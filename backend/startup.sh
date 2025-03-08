#!/bin/sh

# print PID of the current process
echo "Current PID: $$"

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
trap 'echo "[start_docker.sh] Received signal. Shutting down..."; kill -TERM $FASTAPI_PID; wait $FASTAPI_PID; exit' TERM INT

# Wait for all processes to finish
wait $FASTAPI_PID
