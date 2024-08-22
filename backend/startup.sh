# test if postgres is up, and sleep until it is
while ! nc -z $DBNAME $DBPORT; do
  echo "Waiting for ${DB_NAME} to be available..."
  sleep 1
done

python3 create_sql_tables.py
python3 create_admin_user.py
python3 add_tools_to_db.py
# test if REDIS_INTERNAL_PORT is up, and sleep until it is
while ! nc -z agents-redis $REDIS_INTERNAL_PORT; do
  echo "Waiting for ${REDIS_INTERNAL_PORT} to be available..."
  sleep 1
done
celery -A oracle.celery_app.celery_app worker --loglevel=info &
python3 -m hypercorn main:app -b 0.0.0.0:1235 --reload