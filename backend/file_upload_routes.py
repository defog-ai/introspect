import base64
import re
import time
import traceback

from pandas.errors import ParserError
from fastapi import APIRouter, File, Request, UploadFile, HTTPException
from fastapi.responses import JSONResponse, Response
from request_models import (
    DbDetails,
)
from utils_logging import LOGGER
from db_utils import get_db_info, get_db_type_creds
import random
import os
import pandas as pd
from utils_file_uploads import export_df_to_postgres, clean_table_name, ExcelUtils, CSVUtils
from utils_md import set_metadata
from utils_oracle import upload_pdf_files, update_project_files, get_pdf_content, delete_pdf_file
from db_utils import update_db_type_creds
from sqlalchemy_utils import database_exists, create_database
import io
import asyncio

router = APIRouter(
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


async def upload_files_to_db(files, db_name: str | None = None) -> DbDetails:
    """
    Takes in a list of Files, and the contents of each file as a base 64 string.
    We then create a database from the file contents, and
    return the db_name and db_info that is used to store this file.
    """
    if db_name is None:
        cleaned_db_name = clean_table_name(files[0].filename)
    else:
        cleaned_db_name = db_name

    tables = {}

    # convert to dfs
    for f in files:
        try:
            file_name = f.filename
            buffer = f.file.read()

            # Convert array buffer to DataFrame
            if file_name.endswith(".csv"):
                # For CSV files
                df = await CSVUtils.clean_csv_pd(buffer)

                # Further clean dataframe with OpenAI Code Interpreter if needed
                # Dataframe will only be cleaned if it's detected as "dirty"
                # The clean_csv_openai function handles this check internally
                df = await CSVUtils.clean_csv_openai(file_name, df)
                
                table_name = clean_table_name(
                    re.sub(r"\.csv$", "", file_name), existing=tables.keys()
                )

                tables[table_name] = df
            elif file_name.endswith((".xls", ".xlsx")):
                # For Excel files
                excel_file = io.BytesIO(buffer)
                tables = await ExcelUtils.clean_excel_pd(excel_file)

                # Further clean Excel sheets with OpenAI Code Interpreter if needed
                tasks = []
                table_names = []
                for table_name, df in tables.items():
                    # Each sheet's dataframe will only be cleaned if it's detected as "dirty"
                    # The clean_excel_openai function handles this check internally
                    tasks.append(ExcelUtils.clean_excel_openai(table_name, df))
                    table_names.append(table_name)
                tables = dict(zip(table_names, await asyncio.gather(*tasks)))
            else:
                raise Exception(
                    f"Unsupported file format for file: {file_name}. Please upload a CSV or Excel file."
                )

        except ParserError as e:
            traceback.print_exc()
            LOGGER.error(f"Error parsing file {file_name}: {e}")
            raise Exception(f"Error parsing file {file_name}: {e}")
        except Exception as e:
            traceback.print_exc()
            LOGGER.error(f"Error processing file {file_name}: {e}")
            raise Exception(f"Error processing file {file_name}: {e}")

    # Determine which database credentials to use
    # If db_name is provided, check if there are existing db_creds we should use
    db_creds_to_use = INTERNAL_DB_CREDS
    if db_name is not None:
        # Check if user already has db credentials
        db_type_creds = await get_db_type_creds(db_name)
        if db_type_creds and db_type_creds[0] == "postgres" and db_type_creds[1]:
            # Use the user's credentials instead if they exist and are for postgres
            LOGGER.info(f"Using user's existing postgres credentials for {db_name}")
            db_creds_to_use = db_type_creds[1]

    # create the database
    # NOTE: It seems like we cannot use asyncpg in the database_exists and create_database functions, so we are using sync
    # connection uri
    connection_uri = f"postgresql://{db_creds_to_use['user']}:{db_creds_to_use['password']}@{db_creds_to_use['host']}:{db_creds_to_use['port']}/{cleaned_db_name}"
    if database_exists(connection_uri):
        LOGGER.info(
            f"Database already exists: {cleaned_db_name}, but is not added to db creds. Dropping it."
        )
        LOGGER.info(f"Database dropped: {cleaned_db_name}")
    else:
        LOGGER.info(f"Creating database: {cleaned_db_name}")
        create_database(connection_uri)
        LOGGER.info(f"Database created: {cleaned_db_name}")

    # now that the DB is created
    # we will use asyncpg version so we don't block requests
    connection_uri = f"postgresql+asyncpg://{db_creds_to_use['user']}:{db_creds_to_use['password']}@{db_creds_to_use['host']}:{db_creds_to_use['port']}/{cleaned_db_name}"

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

    # Use the same credentials we used for exporting
    user_db_creds = {
        "user": db_creds_to_use["user"],
        "password": db_creds_to_use["password"],
        "host": db_creds_to_use["host"],
        "port": db_creds_to_use["port"],
        "database": cleaned_db_name,
    }
    
    # Only update db_type_creds if we're not using an existing user db or db_name is None
    LOGGER.info(f"Creating Project entry for {cleaned_db_name}")
    await update_db_type_creds(cleaned_db_name, "postgres", user_db_creds)

    db_info = await get_db_info(cleaned_db_name)

    return DbDetails(db_name=cleaned_db_name, db_info=db_info)


@router.post("/upload_files")
async def upload_files(
    request: Request
):
    """
    Upload files to the database.
    Args:
        - db_name: what database to associate the files with? can be blank (new db will be created)
        - files: list of files to upload
    """
    form_data = await request.form()
    token = form_data.get("token")
    db_name = form_data.get("db_name")
    files = form_data.getlist("files")
    LOGGER.info("Received request to upload files")
    # data_files are all those that end with .csv, .xls, or .xlsx
    data_files = [f for f in files if f.filename.endswith(('.csv', '.xls', '.xlsx'))]
    pdf_files = [f for f in files if f.filename.endswith(('.pdf'))]
    
    if len(data_files) > 0:
        if db_name is None:
            new_db = await upload_files_to_db(files=data_files)
            db_name = new_db.db_name
        else:
            await upload_files_to_db(files=data_files, db_name=db_name)
    if len(pdf_files) > 0:
        if db_name is None and len(data_files) == 0:
            raise HTTPException(
                status_code=400,
                detail="To upload PDF files, you must either provide a database name or include at least one CSV/Excel file to create a new database"
            )
        pdf_file_ids = await upload_pdf_files(pdf_files)
        await update_project_files(db_name, pdf_file_ids)

    db_info = await get_db_info(db_name)

    return JSONResponse(status_code=200, content={"message": "Success", "db_name": db_name, "db_info": db_info})


@router.get("/download_pdf/{file_id}")
async def download_pdf(file_id: int):
    """
    Download a PDF file by its ID
    """
    try:
        pdf_data = await get_pdf_content(file_id)
        if not pdf_data:
            return JSONResponse(
                status_code=404,
                content={"error": "PDF file not found"}
            )
        
        # Decode base64 data
        binary_data = base64.b64decode(pdf_data["base64_data"])
        
        # Set the appropriate headers for PDF download
        headers = {
            "Content-Disposition": f"attachment; filename={pdf_data['file_name']}",
            "Content-Type": "application/pdf"
        }
        
        return Response(content=binary_data, headers=headers)
    except Exception as e:
        LOGGER.error(f"Error downloading PDF: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Error downloading PDF: {str(e)}"}
        )


@router.delete("/delete_pdf/{file_id}")
async def delete_pdf(file_id: int, token: str, db_name: str):
    """
    Delete a PDF file by its ID and remove it from the project's associated files
    
    Args:
        file_id: ID of the PDF file to delete
        token: Authentication token
        db_name: Name of the project the file is associated with
    """
    try:
        LOGGER.info(f"Deleting PDF file {file_id} from project {db_name}")
        success = await delete_pdf_file(db_name, file_id)
        
        if not success:
            return JSONResponse(
                status_code=404,
                content={"error": "Failed to delete PDF file"}
            )
        
        # Get updated project info with the new files list
        from db_utils import get_db_info
        db_info = await get_db_info(db_name)
        
        return JSONResponse(
            status_code=200,
            content={"message": "PDF file deleted successfully", "db_info": db_info}
        )
    except Exception as e:
        LOGGER.error(f"Error deleting PDF: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Error deleting PDF: {str(e)}"}
        )


