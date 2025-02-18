from auth_utils import validate_user_request
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from request_models import UploadFileAsDBRequest
from utils_logging import LOGGER
from utils_file_uploads import clean_table_name
from db_utils import get_db_type_creds
import random
import os
import pandas as pd
from utils_file_uploads import export_df_to_postgres, clean_table_name
from utils_md import set_metadata
from db_utils import update_db_type_creds
from sqlalchemy_utils import database_exists, create_database, drop_database

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["File Upload"],
)

# DB creds for the postgres in this docker container
INTERNAL_DB_CREDS = {
    "user": os.environ.get("DBUSER", "postgres"),
    "password": os.environ.get("DBPASSWORD", "postgres"),
    "host": os.environ.get("DBHOST", "agents-postgres"),
    "port": os.environ.get("DBPORT", "5432"),
    "database": os.environ.get("DATABASE", "postgres"),
}


@router.post("/upload_file_as_db")
async def upload_file_as_db(request: UploadFileAsDBRequest):
    """
    Takes in a CSV or Excel file, and the contents of the file as a dict,
    which maps the tables in the file to their contents.
    We then create a database from the file contents, and
    return the db_name that is used to store this file.
    """
    file_name = request.file_name
    tables = request.tables
    LOGGER.info(f"file_name: {file_name}")
    LOGGER.info(f"tables: {tables}")

    cleaned_db_name = clean_table_name(file_name)
    db_exists = await get_db_type_creds(cleaned_db_name)

    if db_exists:
        # add a random 3 digit integer to the end of the file name
        cleaned_db_name = f"{cleaned_db_name}_{random.randint(1, 9999)}"

    # create the database
    # NOTE: It seems like we cannot use asyncpg in the database_exists and create_database functions, so we are using sync
    # connection uri
    connection_uri = f"postgresql://{INTERNAL_DB_CREDS['user']}:{INTERNAL_DB_CREDS['password']}@{INTERNAL_DB_CREDS['host']}:{INTERNAL_DB_CREDS['port']}/{cleaned_db_name}"
    if database_exists(connection_uri):
        LOGGER.info(f"Database already exists: {cleaned_db_name}, but is not added to db creds. Dropping it.")
        drop_database(connection_uri)
        LOGGER.info(f"Database dropped: {cleaned_db_name}")


    LOGGER.info(f"Creating database: {cleaned_db_name}")
    create_database(connection_uri)
    LOGGER.info(f"Database created: {cleaned_db_name}")

    # now that the DB is created
    # we will use asyncpg version so we don't block requests
    connection_uri = f"postgresql+asyncpg://{INTERNAL_DB_CREDS['user']}:{INTERNAL_DB_CREDS['password']}@{INTERNAL_DB_CREDS['host']}:{INTERNAL_DB_CREDS['port']}/{cleaned_db_name}"

    db_metadata = []

    for table_name in tables:
        cleaned_table_name = clean_table_name(table_name)
        # convert the content of each table into a pandas df
        df = pd.DataFrame(
            tables[table_name].rows,
            columns=[i.title for i in tables[table_name].columns],
            # store all values as strings to preserve dirty data
            dtype=str,
        )
        inferred_types = (await export_df_to_postgres(df, cleaned_table_name, connection_uri, chunksize=5000))["inferred_types"]
        for col, dtype in inferred_types.items():
            db_metadata.append({
                "db_name": cleaned_db_name,
                "table_name": cleaned_table_name,
                "column_name": col,
                "data_type": dtype
            })
    
    LOGGER.info(f"Adding metadata for {cleaned_db_name}")
    await set_metadata(cleaned_db_name, db_metadata)

    user_db_creds = {
        "user": INTERNAL_DB_CREDS["user"],
        "password": INTERNAL_DB_CREDS["password"],
        "host": INTERNAL_DB_CREDS["host"],
        "port": INTERNAL_DB_CREDS["port"],
        "database": cleaned_db_name
    }
    LOGGER.info(f"Creating DbCreds entry for {cleaned_db_name}")
    await update_db_type_creds(cleaned_db_name, "postgres", user_db_creds)

    return JSONResponse(content={"db_name": cleaned_db_name})