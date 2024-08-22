# if INTERAL_DB is sqlite, then create the sqlite tables. Else, create postgres tables
if [ "$INTERNAL_DB" = "sqlite" ]; then
  echo "Using sqlite as internal database"
  python3 create_sql_tables.py --db_type sqlite
else
  echo "Using postgres as internal database"
  python3 create_sql_tables.py --db_type sqlite
fi
python3 create_admin_user.py
python3 add_tools_to_db.py
# test if REDIS_INTERNAL_PORT is up, and sleep until it is
while ! nc -z agents-redis $REDIS_INTERNAL_PORT; do
  echo "Waiting for ${REDIS_INTERNAL_PORT} to be available..."
  sleep 1
done
celery -A oracle.celery_app.celery_app worker --loglevel=info &
python3 -m hypercorn main:app -b 0.0.0.0:1235 --reload