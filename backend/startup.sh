# create empty report assets dirs
mkdir -p /agents-assets/report-assets
mkdir -p /agents-assets/report-assets/boxplots 
mkdir -p /agents-assets/report-assets/datasets 
mkdir -p /agents-assets/report-assets/heatmaps 
mkdir -p /agents-assets/report-assets/linechart 
mkdir -p /agents-assets/report-assets/linecharts
touch /agent-logs-out

python3 create_sqlite_tables.py
python3 create_admin_user.py
python3 add_tools_to_db.py
# test if REDIS_INTERNAL_PORT is up, and sleep until it is
while ! nc -z agents-redis $REDIS_INTERNAL_PORT; do
  echo "Waiting for ${REDIS_INTERNAL_PORT} to be available..."
  sleep 1
done
celery -A oracle.celery_app.celery_app worker --loglevel=info &
python3 -m hypercorn main:app -b 0.0.0.0:1235 --reload