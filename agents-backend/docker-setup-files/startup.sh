python3 create_admin_user.py

# write OPENAI_API_KEY which is the first argument passed to this bash script
# to /agents-python-server/.env.yaml
# with new lines before and after it
# supervisor does not seem ot have acess to parent env vars.
# so this hacky way to let our code access it

echo -e "\nOPENAI_API_KEY: \"$1\"\n" >> /agents-python-server/.env.yaml

# while testing, we can just do this instead of running the server with supervisor for easier debugging
# in prod, we will run the server with supervisor, and this line will be commented out
python3 -u -m hypercorn main:app -b 0.0.0.0:1235

# service supervisor stop
# service supervisor start

# supervisorctl restart all