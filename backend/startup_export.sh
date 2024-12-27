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
while ! nc -z $REDIS_INTERNAL_HOST $REDIS_INTERNAL_PORT; do
  echo "Waiting for ${REDIS_INTERNAL_PORT} to be available..."
  sleep 1
done
python3 -m hypercorn main:app -b 0.0.0.0:1235 &

# Wait for all background jobs to finish
wait