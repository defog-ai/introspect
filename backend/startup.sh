echo "Running startup.sh"
# test if postgres is up, and sleep until it is
# if INTERNAL_DB is postgres, then wait for postgres to be up
if [ "$INTERNAL_DB" = "postgres" ]; then
  while ! nc -z $DBHOST $DBPORT; do
    echo "Waiting for ${DBHOST} to be available..."
    sleep 1
  done
fi

python3 create_sql_tables.py
python3 create_admin_user.py
python3 add_tools_to_db.py
# test if REDIS_INTERNAL_PORT is up, and sleep until it is
while ! nc -z agents-redis $REDIS_INTERNAL_PORT; do
  echo "Waiting for ${REDIS_INTERNAL_PORT} to be available..."
  sleep 1
done
celery -A oracle.celery_app.celery_app worker --loglevel=info &
python3 -m hypercorn main:app -b 0.0.0.0:1235 --reload &

# Test for the RabbitMQ server to be up before starting the consumers
max_retries=30
count=0
echo "Waiting for RabbitMQ server to be up..."
while ! nc -z agents-rabbitmq 5672; do
    sleep 1
    count=$((count+1))
    if [ "$count" -ge "$max_retries" ]; then
       echo "RabbitMQ server did not become available after $max_retries attempts. Exiting."
       exit 1
    fi
done
if [ "$count" -gt 0 ]; then
    echo "RabbitMQ server is up."
fi

# Start consumers in the background
python3 consumer_google_analytics.py &
python3 consumer_stripe.py &

# Wait for all background jobs to finish
wait