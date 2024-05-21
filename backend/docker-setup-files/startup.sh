python3 create_admin_user.py
python3 add_tools_to_db.py

echo -e "\nOPENAI_API_KEY: \"$1\"\n" >> /agents-python-server/.env.yaml

python3 -u -m hypercorn main:app -b 0.0.0.0:1235