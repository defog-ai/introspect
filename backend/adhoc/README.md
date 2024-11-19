# Adhoc Data

You can use these scripts for inserting / initializing your DSH instance with user data.

## Insert User DB Creds

You can start by adding the following api_key's and key names to your `.env` file like below:

```sh
DEFOG_API_KEYS="456,123,test_restaurant,test_macmillan"
DEFOG_API_KEY_NAMES="Housing,Cards,Restaurant,Macmillan" # feel free to edit to whatever you want displayed on the UI
```

This script inserts multiple test user and db creds data into the database, so that we can skip the db connection setup step on the UI. It needs to be run from within the docker container as such:

```sh
$ docker exec -it defog-self-hosted-agents-python-server-1 /bin/bash -c "python adhoc/insert_user_db_creds.py"
```
