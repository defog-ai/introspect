python3 create_admin_user.py

# write OPENAI_API_KEY which is the first argument passed to this bash script
# to /agents-python-server/.env.yaml
# with new lines before and after it
# supervisor does not seem ot have acess to parent env vars.
# so this hacky way to let our code access it

echo -e "\nOPENAI_API_KEY: \"$1\"\n" >> /agents-python-server/.env.yaml

service supervisor stop
service supervisor start

supervisorctl restart all