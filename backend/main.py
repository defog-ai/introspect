import logging
import os
import traceback

from fastapi.responses import JSONResponse
from sqlalchemy import insert, text, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy_utils import create_database, database_exists, drop_database

from db_models import DbCreds
from db_utils import get_db_names, get_db_type_creds
from utils import clean_table_name
from request_models import UploadFileAsDBRequest
import instructions_routes
import admin_routes, agent_routes, auth_routes, csv_routes, doc_endpoints, golden_queries_routes, imported_tables_routes, integration_routes, metadata_routes, oracle_report_routes, oracle_routes, query_routes, slack_routes, tools.tool_routes, user_history_routes, xdb_routes
from db_analysis_utils import get_analysis_data, initialise_analysis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from startup import lifespan
from db_config import engine

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("server")

app = FastAPI(lifespan=lifespan)

app.include_router(admin_routes.router)
app.include_router(agent_routes.router)
app.include_router(auth_routes.router)
app.include_router(csv_routes.router)
app.include_router(doc_endpoints.router)
app.include_router(golden_queries_routes.router)
app.include_router(imported_tables_routes.router)
app.include_router(instructions_routes.router)
app.include_router(integration_routes.router)
app.include_router(metadata_routes.router)
app.include_router(oracle_report_routes.router)
app.include_router(oracle_routes.router)
app.include_router(query_routes.router)
app.include_router(slack_routes.router)
app.include_router(tools.tool_routes.router)
app.include_router(user_history_routes.router)
app.include_router(xdb_routes.router)
from oracle.setup import setup_dir

# check if the oracle directory structure exists and create if not
setup_dir(os.getcwd())


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

request_types = ["clarify", "understand", "gen_steps", "gen_analysis"]
llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")

# DB creds for the postgres in this docker container
db_creds = {
    "user": os.environ.get("DBUSER", "postgres"),
    "password": os.environ.get("DBPASSWORD", "postgres"),
    "host": os.environ.get("DBHOST", "agents-postgres"),
    "port": os.environ.get("DBPORT", "5432"),
    "database": os.environ.get("DATABASE", "postgres"),
}


@app.get("/ping")
async def root():
    return {"message": "Hello World"}


edit_request_types_and_prop_names = {
    "edit_analysis_md": {
        "table_column": "gen_analysis",
        "prop_name": "analysis_sections",
    },
    "edit_approaches": {"table_column": "gen_approaches", "prop_name": "approaches"},
}


@app.post("/get_analysis")
async def one_analysis(request: Request):
    try:
        params = await request.json()
        analysis_id = params.get("analysis_id")

        print("get_one_analysis", params)

        err, analysis_data = await get_analysis_data(analysis_id)

        if err is not None:
            return {"success": False, "error_message": err}

        return {"success": True, "analysis_data": analysis_data}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"success": False, "error_message": "Incorrect request"}


@app.post("/create_analysis")
async def create_analysis(request: Request):
    try:
        params = await request.json()
        token = params.get("token")

        db_name = params.get("db_name")
        print("create_analysis", params)

        err, analysis_data = await initialise_analysis(
            user_question="",
            token=token,
            db_name=db_name,
            custom_id=params.get("custom_id"),
            other_initialisation_details=params.get(
                "initialisation_details",
                params.get(
                    "other_data",
                ),
            ),
        )

        if err is not None:
            return {"success": False, "error_message": err}

        return {"success": True, "analysis_data": analysis_data}
    except Exception as e:
        print(e)
        return {"success": False, "error_message": "Incorrect request"}


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/get_api_key_names")
async def get_api_key_names(request: Request):
    # DEFOG_API_KEY_NAMES = os.environ.get("DEFOG_API_KEY_NAMES")
    # db_names = DEFOG_API_KEY_NAMES.split(",")

    return {"api_key_names": await get_db_names()}


@app.post("/upload_file_as_db")
async def upload_file_as_db(request: UploadFileAsDBRequest):
    """
    Takes in a file name, and the contents of the file as a dict which maps the tables in the file to their contents.

    We do some checks to make sure the file name is valid and a db with that file name doesn't already exist, and construct a db_name from the file name if necessary.

    Returns the db_name that is used to store this file.
    """
    file_name = request.file_name
    tables = request.tables
    LOGGER.info(f"file_name: {file_name}")
    LOGGER.info(f"tables: {tables}")

    cleaned_file_name = clean_table_name(file_name)

    exists = await get_db_type_creds(cleaned_file_name)

    if exists:
        # add a random 3 digit integer to the end of the file name
        import random

        cleaned_file_name = f"{cleaned_file_name}_{random.randint(100, 999)}"

    # create the database
    # NOTE: It seems like we cannot use asyncpg in the database_exists and create_database functions, so we are using normal
    # connection uri
    connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{cleaned_file_name}"
    if database_exists(connection_uri):
        LOGGER.info(f"Database already exists: {cleaned_file_name}, but is not added to db creds. Dropping it.")
        drop_database(connection_uri)
        LOGGER.info(f"Database dropped: {cleaned_file_name}")


    LOGGER.info(f"Creating database: {cleaned_file_name}")
    create_database(connection_uri)
    LOGGER.info(f"Database created: {cleaned_file_name}")

    # going forward, we will use the asyncpg version
    connection_uri = f"postgresql+asyncpg://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{cleaned_file_name}"

    user_db_engine = create_async_engine(connection_uri)

    async with user_db_engine.begin() as conn:
        # create the tables in the database
        for table_name, table_data in tables.items():
            rows = table_data.rows
            columns = table_data.columns
            # guess the postgrescolumn types of this table from the first non null entry
            # default to string
            column_types = {}
            for column in columns:
                column_name = column.title
                column_types[column_name] = "string"

                for row in rows:
                    if row[column_name] is not None:
                        if column_types[column_name] == "datetime":
                            column_types[column_name] = "timestamp"
                        if column_types[column_name] == "int":
                            column_types[column_name] = "integer"
                        if column_types[column_name] == "float":
                            column_types[column_name] = "double precision"
                        if column_types[column_name] == "bool":
                            column_types[column_name] = "boolean"
                        if column_types[column_name] == "string":
                            column_types[column_name] = "varchar"
                        
                        break

            # create the table in the database
            # create a table in this database
            LOGGER.info(f"Creating table: {table_name} with columns: {columns}")
            
            stmt = f"CREATE TABLE IF NOT EXISTS {table_name} ("

            stmt += f"{', '.join([f'{col.title} {column_types[col.title]}' for col in columns])}"

            stmt += ");"

            LOGGER.info(stmt)
            await conn.execute(
                text(stmt),
            )

            LOGGER.info(f"Inserting rows into table: {table_name}")
            stmt = f"INSERT INTO {table_name} ({', '.join([x.title for x in columns])}) VALUES \n"
            
            for idx, row in enumerate(rows):
                stmt += "("
                stmt += ", ".join([f"'{row.get(column.title, "null")}'" for column in columns])
                stmt += ")"
                if idx < len(rows) - 1:
                    stmt += ",\n"
                else:
                    stmt += ";"

            LOGGER.info(stmt)
            await conn.execute(
                text(stmt),
            )

    async with engine.begin() as conn:
        LOGGER.info(f"Creating DbCreds entry for {cleaned_file_name}")
        # finally, if all succeeds, add the credentials to db creds
        await conn.execute(
            insert(DbCreds).values(
            db_name=cleaned_file_name, db_type="postgres", db_creds=db_creds
            )
        )

    return JSONResponse(content={"db_name": cleaned_file_name})
