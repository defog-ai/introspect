import base64
import re
import time
from auth_utils import validate_user_request
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from request_models import (
    DbDetails,
    UploadFileAsDBRequest,
    UploadMultipleFilesAsDBRequest,
    DataFile,
)
from utils_logging import LOGGER
from utils_file_uploads import clean_table_name
from db_utils import get_db_info, get_db_type_creds
import random
import os
import pandas as pd
from utils_file_uploads import export_df_to_postgres, clean_table_name
from utils_md import set_metadata
from db_utils import update_db_type_creds
from sqlalchemy_utils import database_exists, create_database, drop_database
import io

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


async def upload_files_as_db(files: list[DataFile]) -> DbDetails:
    """
    Takes in a list of DataFiles, and the contents of each file as a base 64 string.
    We then create a database from the file contents, and
    return the db_name and db_info that is used to store this file.
    """
    cleaned_db_name = clean_table_name(files[0].file_name)
    db_exists = await get_db_type_creds(cleaned_db_name)

    if db_exists:
        # add a random 3 digit integer to the end of the file name
        cleaned_db_name = f"{cleaned_db_name}_{random.randint(1, 9999)}"

    tables = {}

    # convert to dfs
    for f in files:
        file_name = f.file_name
        buffer = base64.b64decode(f.base64_content)

        # Convert array buffer to DataFrame
        if file_name.endswith(".csv"):
            # For CSV files
            df = pd.read_csv(io.StringIO(buffer.decode("utf-8")))

            table_name = clean_table_name(
                re.sub(r"\.csv$", "", file_name), existing=tables.keys()
            )

            tables[table_name] = df
        elif file_name.endswith((".xls", ".xlsx")):
            # For Excel files
            df = pd.ExcelFile(io.BytesIO(buffer))
            for sheet_name in df.sheet_names:
                table_name = clean_table_name(sheet_name, existing=tables.keys())
                tables[table_name] = df.parse(sheet_name)
        else:
            raise Exception(
                f"Unsupported file format for file: {file_name}. Please upload a CSV or Excel file."
            )

    # create the database
    # NOTE: It seems like we cannot use asyncpg in the database_exists and create_database functions, so we are using sync
    # connection uri
    connection_uri = f"postgresql://{INTERNAL_DB_CREDS['user']}:{INTERNAL_DB_CREDS['password']}@{INTERNAL_DB_CREDS['host']}:{INTERNAL_DB_CREDS['port']}/{cleaned_db_name}"
    if database_exists(connection_uri):
        LOGGER.info(
            f"Database already exists: {cleaned_db_name}, but is not added to db creds. Dropping it."
        )
        drop_database(connection_uri)
        LOGGER.info(f"Database dropped: {cleaned_db_name}")

    LOGGER.info(f"Creating database: {cleaned_db_name}")
    create_database(connection_uri)
    LOGGER.info(f"Database created: {cleaned_db_name}")

    # now that the DB is created
    # we will use asyncpg version so we don't block requests
    connection_uri = f"postgresql+asyncpg://{INTERNAL_DB_CREDS['user']}:{INTERNAL_DB_CREDS['password']}@{INTERNAL_DB_CREDS['host']}:{INTERNAL_DB_CREDS['port']}/{cleaned_db_name}"

    db_metadata = []

    for table_name, table_df in tables.items():
        start = time.time()
        LOGGER.info(f"Parsing table: {table_name}")
        inferred_types = (
            await export_df_to_postgres(
                table_df, table_name, connection_uri, chunksize=5000
            )
        )["inferred_types"]

        LOGGER.info(f"Inferred types: {inferred_types}")

        end = time.time()
        LOGGER.info(f"Export to db for table {table_name} took {end - start} seconds")

        for col, dtype in inferred_types.items():
            db_metadata.append(
                {
                    "db_name": cleaned_db_name,
                    "table_name": table_name,
                    "column_name": col,
                    "data_type": dtype,
                }
            )

    LOGGER.info(f"Adding metadata for {cleaned_db_name}")
    await set_metadata(cleaned_db_name, db_metadata)

    user_db_creds = {
        "user": INTERNAL_DB_CREDS["user"],
        "password": INTERNAL_DB_CREDS["password"],
        "host": INTERNAL_DB_CREDS["host"],
        "port": INTERNAL_DB_CREDS["port"],
        "database": cleaned_db_name,
    }
    LOGGER.info(f"Creating DbCreds entry for {cleaned_db_name}")
    await update_db_type_creds(cleaned_db_name, "postgres", user_db_creds)

    db_info = await get_db_info(cleaned_db_name)

    return DbDetails(db_name=cleaned_db_name, db_info=db_info)


@router.post("/upload_file_as_db")
async def upload_file_as_db(request: UploadFileAsDBRequest):
    """
    Takes in a CSV or Excel file, and the contents of the file as a dict,
    which maps the tables in the file to their contents.
    We then create a database from the file contents, and
    return the db_name that is used to store this file.
    """
    file_name = request.file_name
    base64_content = request.base64_content

    LOGGER.info(f"file_name: {file_name}")
    LOGGER.info(f"base64_content length: {len(base64_content)}")

    try:
        new_db = await upload_files_as_db(
            [
                DataFile(
                    file_name=file_name,
                    base64_content=base64_content,
                )
            ]
        )
    except Exception as e:
        LOGGER.error(f"Error uploading file as db: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Error uploading file as db"}
        )

    db_info = new_db.db_info
    cleaned_db_name = new_db.db_name

    return JSONResponse(content={"db_info": db_info, "db_name": cleaned_db_name})


@router.post("/upload_multiple_files_as_db")
async def upload_multiple_files_as_db_endpoint(
    request: UploadMultipleFilesAsDBRequest,
) -> DbDetails:
    """
    Loads of DRY code from upload_file_as_db.

    Takes in a list of CSV or Excel files, and the contents of each file as a base 64 string.
    We pick the first file, create a db_name from it, and upload the rest of the files to that db as tables.
    Dealing with csvs and excels is similar to the upload_file_as_db endpoint, just the db_name calculation is slightly different.
    """
    files = request.files

    try:
        new_db = await upload_files_as_db(files)
    except Exception as e:
        LOGGER.error(f"Error uploading file as db: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Error uploading file as db"}
        )

    db_info = new_db.db_info
    cleaned_db_name = new_db.db_name

    return JSONResponse(content={"db_info": db_info, "db_name": cleaned_db_name})
