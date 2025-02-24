# Adhoc Data

You can use these scripts for inserting / initializing your DSH instance with user data.

## OAuth Accounts

If you would like to give admin access to your Google account, you can add your email as a dictionary inside the `users` list in the `insert_user_db_creds.py` file.

No password is needed for Google accounts if we're using OAuth.

```python
users = [
    ...
    {
        "username": "jp@defog.ai", # no password needed
    },
]
```

## Insert User DB Creds

Next, update the `insert_user_db_creds.py` file with the db name and db creds data in a dictionary in the `databases` list. Then, run the following command to insert the data into the database:

```sh
$ docker exec -it defog-self-hosted-agents-python-server-1 /bin/bash -c "python adhoc/insert_user_db_creds.py"
```

This script is idempotent, so it can be run multiple times without any issues. We will update the existing users and db creds if they already exist, instead of throwing an error or creating duplicates.

## Insert Metadata

We can also insert metadata for the imported tables. Update the `insert_metadata.py` file with your desired metadata as a dictionary whose keys are the table names and values are lists of dictionaries, each containing the metadata for a column. Then, run the following command to insert the data into the database:

```sh
$ docker exec -it defog-self-hosted-agents-python-server-1 /bin/bash -c "python adhoc/insert_metadata.py"
```

This script is idempotent, so it can be run multiple times without any issues. We will update the existing metadata if it already exists, instead of throwing an error or creating duplicates.
