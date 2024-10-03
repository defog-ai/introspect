import inspect
import re
import logging
import traceback
import datetime
import uuid
import pandas as pd
from sqlalchemy import (
    create_engine,
    select,
    update,
    insert,
    delete,
    inspect as sql_inspect,
    Table,
    MetaData,
    text,
)
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.automap import automap_base
from utils_logging import LOGGER

import asyncio
from utils import warn_str, YieldList
from generic_utils import make_request
import os

import redis

REDIS_HOST = os.getenv("REDIS_INTERNAL_HOST", "agents-redis")
REDIS_PORT = os.getenv("REDIS_INTERNAL_PORT", 6379)
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)

analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)
INTERNAL_DB = os.environ.get("INTERNAL_DB", None)
IMPORTED_TABLES_DBNAME = os.environ.get("IMPORTED_TABLES_DBNAME", "imported_tables")

if INTERNAL_DB == "sqlite":
    print("using sqlite as our internal db")
    # if using sqlite
    connection_uri = "sqlite:///defog_local.db"
    engine = create_engine(connection_uri, connect_args={"timeout": 3})
    imported_tables_engine = create_engine(
        f"sqlite:///{IMPORTED_TABLES_DBNAME}.db", connect_args={"timeout": 3}
    )
elif INTERNAL_DB == "postgres":
    db_creds = {
        "user": os.environ.get("DBUSER", "postgres"),
        "password": os.environ.get("DBPASSWORD", "postgres"),
        "host": os.environ.get("DBHOST", "agents-postgres"),
        "port": os.environ.get("DBPORT", "5432"),
        "database": os.environ.get("DATABASE", "postgres"),
    }

    # if using postgres
    print("using postgres as our internal db")
    connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
    engine = create_engine(connection_uri)
    if IMPORTED_TABLES_DBNAME == db_creds["database"]:
        print(
            f"IMPORTED_TABLES_DBNAME is the same as the main database: {IMPORTED_TABLES_DBNAME}. Consider use a different database name."
        )
    imported_tables_engine = create_engine(
        f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{IMPORTED_TABLES_DBNAME}"
    )
elif INTERNAL_DB == "sqlserver":
    db_creds = {
        "user": os.environ.get("DBUSER", "sa"),
        "password": os.environ.get("DBPASSWORD", "Password1"),
        "host": os.environ.get("DBHOST", "localhost"),
        "database": os.environ.get("DATABASE", "defog"),
        "port": os.environ.get("DBPORT", "1433"),
    }

    # if using sqlserver
    connection_uri = f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}?driver=ODBC+Driver+18+for+SQL+Server"
    engine = create_engine(connection_uri)

    if IMPORTED_TABLES_DBNAME == db_creds["database"]:
        print(
            f"IMPORTED_TABLES_DBNAME is the same as the main database: {IMPORTED_TABLES_DBNAME}. Consider using a different database name."
        )
    imported_tables_engine = create_engine(
        f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{IMPORTED_TABLES_DBNAME}?driver=ODBC+Driver+18+for+SQL+Server"
    )

Base = automap_base()
# reflect the tables
Base.prepare(autoload_with=engine)

ImportedTablesBase = automap_base()
ImportedTablesBase.prepare(autoload_with=imported_tables_engine)

Docs = Base.classes.defog_docs
RecentlyViewedDocs = Base.classes.defog_recently_viewed_docs
Analyses = Base.classes.defog_analyses
TableCharts = Base.classes.defog_table_charts
Tools = Base.classes.defog_tools
Users = Base.classes.defog_users
Feedback = Base.classes.defog_plans_feedback
DbCreds = Base.classes.defog_db_creds
OracleSources = Base.classes.oracle_sources
OracleClarifications = Base.classes.oracle_clarifications
OracleReports = Base.classes.oracle_reports

ImportedTables = ImportedTablesBase.classes.imported_tables


def update_imported_tables_db(
    link: str,
    table_index: int,
    new_table_name: str,
    data: list[list[str, str]],
    schema_name: str,
) -> bool:
    """
    Updates the IMPORTED_TABLES_DBNAME database with the new schema and table.
    Replaces table from IMPORTED_TABLES_DBNAME database if it already exists.
    data is a list of lists where the first list consists of the column names and the rest are the rows.
    This function should always precede `update_imported_tables` as it first retrieves the old table name if the
    table (defined by its link/index) already exists in the internal database.
    """
    with imported_tables_engine.begin() as imported_tables_connection:
        # create schema in imported_tables db if it doesn't exist
        try:
            if INTERNAL_DB == "postgres":
                # check if schema exists
                inspector = sql_inspect(imported_tables_engine)
                schema_names = inspector.get_schema_names()
                schema_exists = schema_name in schema_names
                if not schema_exists:
                    create_schema_stmt = f"CREATE SCHEMA {schema_name};"
                    imported_tables_connection.execute(text(create_schema_stmt))
                    LOGGER.info(
                        f"Created schema `{schema_name}` in {IMPORTED_TABLES_DBNAME} database."
                    )
            else:
                LOGGER.error(f"INTERNAL_DB is not postgres. Cannot create schema.")
                return False
        except Exception as e:
            LOGGER.error(
                f"Error creating schema `{schema_name}` in {IMPORTED_TABLES_DBNAME} database: {e}"
            )
            return False

        # check if link and table_index already exist in imported_tables of internal database
        with imported_tables_engine.begin() as conn:
            stmt = select(ImportedTables.table_name).where(
                ImportedTables.table_link == link,
                ImportedTables.table_position == table_index,
            )
            result = conn.execute(stmt)
            scalar_result = result.scalar()

            if scalar_result is not None:
                LOGGER.info(
                    f"Entry `{link}` in position `{table_index}` already exists in imported_tables of the internal database."
                )
                # get old table name without schema
                table_name = scalar_result
                table_name = table_name.split(".")[-1]
                LOGGER.info(
                    f"Previous table name: `{table_name}`, New table name:  `{new_table_name}`"
                )

                # drop old table name if it already exists in imported_tables database
                inspector = sql_inspect(imported_tables_engine)
                table_exists = inspector.has_table(table_name, schema=schema_name)
                if table_exists:
                    table = Table(table_name, MetaData(), schema=schema_name)
                    drop_stmt = DropTable(table, if_exists=True)
                    imported_tables_connection.execute(drop_stmt)
                    LOGGER.info(
                        f"Dropped existing table `{table_name}` from {IMPORTED_TABLES_DBNAME} database, schema `{schema_name}`."
                    )
        try:
            # insert the new table into imported_tables database
            save_csv_to_db(
                new_table_name, data, db=IMPORTED_TABLES_DBNAME, schema_name=schema_name
            )
            LOGGER.info(
                f"Inserted table `{new_table_name}` into {IMPORTED_TABLES_DBNAME} database, schema `{schema_name}`."
            )
            return True
        except Exception as e:
            LOGGER.error(
                f"Error inserting table `{new_table_name}` into {IMPORTED_TABLES_DBNAME} database, schema `{schema_name}`: {e}\n Data: {data}"
            )
            return False


def convert_cols_to_jsonb(
    table_name: str, json_cols: list[str], schema_name: str
) -> bool:
    """
    Converts the columns in json_cols to jsonb in the table in the schema of the imported_tables database.
    """
    if INTERNAL_DB == "postgres":
        try:
            with imported_tables_engine.begin() as imported_tables_connection:
                for col in json_cols:
                    stmt = f"ALTER TABLE {schema_name}.{table_name} ALTER COLUMN {col} SET DATA TYPE JSONB USING {col}::JSONB;"
                    imported_tables_connection.execute(text(stmt))
                    LOGGER.info(
                        f"Converted column `{col}` to jsonb in table `{table_name}` in schema `{schema_name}` of {IMPORTED_TABLES_DBNAME} database."
                    )
                return True
        except Exception as e:
            LOGGER.error(
                f"Error converting column `{col}` to jsonb in table `{table_name}` in schema `{schema_name}` of {IMPORTED_TABLES_DBNAME} database: {e}"
            )
            return False
    else:
        LOGGER.error(f"INTERNAL_DB is not postgres. Cannot convert columns to jsonb.")
        return False


def update_imported_tables(
    link: str, table_index: int, table_name: str, table_description: str
) -> bool:
    """
    Updates the imported_tables table in the internal database with the table's info.
    Removes entry from imported_tables of the internal database if it already exists.
    """
    with imported_tables_engine.begin() as conn:
        # check if link and table_index already exist in imported_tables of internal database
        stmt = select(ImportedTables).where(
            ImportedTables.table_link == link,
            ImportedTables.table_position == table_index,
        )
        result = conn.execute(stmt)
        scalar_result = result.scalar()

        if scalar_result is not None:
            try:
                # update imported_tables of the internal database
                update_stmt = (
                    update(ImportedTables)
                    .where(
                        ImportedTables.table_link == link,
                        ImportedTables.table_position == table_index,
                    )
                    .values(table_name=table_name, table_description=table_description)
                )
                conn.execute(update_stmt)
                LOGGER.info(
                    f"Updated entry `{table_name}` in imported_tables of the internal database."
                )
                return True
            except Exception as e:
                LOGGER.error(
                    f"Error occurred in updating entry `{table_name}` in imported_tables of the internal database.: {e}"
                )
                return False
        else:
            try:
                # insert the table's info into imported_tables of the internal database
                table_data = {
                    "table_link": link,
                    "table_position": table_index,
                    "table_name": table_name,
                    "table_description": table_description,
                }
                stmt = insert(ImportedTables).values(table_data)
                conn.execute(stmt)
                LOGGER.info(
                    f"Inserted entry `{table_name}` into imported_tables of the internal database."
                )
                return True
            except Exception as e:
                LOGGER.error(
                    f"Error occurred in inserting entry `{table_name}` into imported_tables of the internal database: {e}"
                )
                return False


def determine_date_format(value):
    """
    Determines the format of the date string.
    """
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    time_pattern = r"^\d{2}:\d{2}:\d{2}$"
    datetime_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"

    if re.match(datetime_pattern, value):
        return "datetime"
    elif re.match(date_pattern, value):
        return "date"
    elif re.match(time_pattern, value):
        return "time"
    else:
        return "string"


def save_csv_to_db(
    table_name: str,
    data: list[list[str, str]],
    db: str = INTERNAL_DB,
    schema_name: str = None,
) -> bool:
    """
    Saves a csv file to either the internal db or the imported_tables db.
    data is a list of lists where the first list consists of the column names and the rest are the rows.
    """
    df = pd.DataFrame(data[1:], columns=data[0])
    # remove empty columns
    if "" in df.columns:
        del df[""]
    # convert date, time, and datetime columns to their respective types
    for col in df.columns:
        if df[col].dtype == "object":
            # Check format of the first non-null item
            nonnull_val = df[col].dropna().iloc[0]
            format_type = determine_date_format(nonnull_val)
            if format_type == "datetime":
                df[col] = pd.to_datetime(df[col])
            elif format_type == "date":
                df[col] = pd.to_datetime(df[col]).dt.date
            elif format_type == "time":
                df[col] = pd.to_datetime(df[col], format="%H:%M:%S").dt.time

    if db == IMPORTED_TABLES_DBNAME:
        engine = imported_tables_engine
    try:
        df.to_sql(
            table_name, engine, if_exists="replace", index=False, schema=schema_name
        )
        return True
    except Exception as e:
        LOGGER.error(e)
        return False


def get_db_type_creds(api_key):
    with engine.begin() as conn:
        row = conn.execute(
            select(DbCreds.db_type, DbCreds.db_creds).where(DbCreds.api_key == api_key)
        ).fetchone()

    LOGGER.debug(row)

    return row


def update_db_type_creds(api_key, db_type, db_creds):
    with engine.begin() as conn:
        # first, check if the record exists
        record = conn.execute(
            select(DbCreds).where(DbCreds.api_key == api_key)
        ).fetchone()

        if record:
            conn.execute(
                update(DbCreds)
                .where(DbCreds.api_key == api_key)
                .values(db_type=db_type, db_creds=db_creds)
            )
        else:
            conn.execute(
                insert(DbCreds).values(
                    api_key=api_key, db_type=db_type, db_creds=db_creds
                )
            )

    return True


def validate_user(token, user_type=None, get_username=False):
    with engine.begin() as conn:
        user = conn.execute(
            select(Users).where(Users.hashed_password == token)
        ).fetchone()

    if user:
        if user_type == "admin":
            if user.user_type == "admin":
                if get_username:
                    return user[1]
                else:
                    return True
            else:
                return False
        else:
            if get_username:
                return user[1]
            else:
                return True
    else:
        return False


def get_user_key_names(token):
    """
    Returns the key names that a user can access based on their token.
    If the user is an admin, they can access all the keys.
    If the user is not an admin, they can only access the keys in their allowed_dbs list.
    Returning `None` or an empty string means the user can access all keys.
    Returning "Invalid token" means the token is invalid.
    """
    with engine.begin() as conn:
        user = conn.execute(
            select(Users).where(Users.hashed_password == token)
        ).fetchone()

    if not user:
        return "Invalid token"

    if user.user_type == "admin":
        return None

    else:
        return user.allowed_dbs


async def execute_code(
    code_snippets: list,  # list of code strings to execute
    fn_name=None,  # function name to call
    use_globals=False,  # whether to use globals as the sandbox
):
    """
    Runs code string and returns output.
    """
    err = None
    out = None
    try:
        sandbox = {}
        if use_globals:
            sandbox = globals()

        for code in code_snippets:
            exec(code, sandbox)

        if fn_name:
            # check if test_tool is an async function
            if inspect.iscoroutinefunction(sandbox[fn_name]):
                out = await sandbox[fn_name]()
            else:
                out = sandbox[fn_name]()
    except Exception as e:
        out = None
        err = str(e)
        sandbox = None
        traceback.print_exc()
    finally:
        return err, out, sandbox


async def initialise_analysis(
    user_question, token, api_key, custom_id=None, other_initialisation_details={}
):
    username = validate_user(token, get_username=True)
    if not username:
        return "Invalid token.", None

    err = None
    timestamp = str(datetime.datetime.now())
    new_analysis_data = None

    try:
        """Create a new analyis in the defog_analyses table"""
        with engine.begin() as conn:
            if not custom_id or custom_id == "":
                analysis_id = str(uuid.uuid4())
            else:
                analysis_id = custom_id
            print("Creating new analyis with uuid: ", analysis_id)
            new_analysis_data = {
                "user_question": user_question,
                "timestamp": timestamp,
                "analysis_id": analysis_id,
                "api_key": api_key,
                "username": username,
            }
            if (
                other_initialisation_details is not None
                and type(other_initialisation_details) is dict
            ):
                new_analysis_data.update(other_initialisation_details)

            conn.execute(insert(Analyses).values(new_analysis_data))
            # if other data has parent_analyses, insert analysis_id into the follow_up_analyses column, which is an array, of all the parent analyses
            if (
                other_initialisation_details is not None
                and type(other_initialisation_details) is dict
                and other_initialisation_details.get("parent_analyses") is not None
            ):
                for parent_analysis_id in other_initialisation_details.get(
                    "parent_analyses"
                ):
                    # get the parent analysis
                    parent_analysis = conn.execute(
                        select(Analyses).where(
                            Analyses.analysis_id == parent_analysis_id
                        )
                    ).fetchone()
                    if parent_analysis is not None:
                        parent_analysis = parent_analysis._mapping
                        # get the follow_up_analyses array
                        follow_up_analyses = (
                            parent_analysis.get("follow_up_analyses") or []
                        )
                        # add the analysis_id to the array
                        follow_up_analyses.append(analysis_id)
                        # update the row
                        conn.execute(
                            update(Analyses)
                            .where(Analyses.analysis_id == parent_analysis_id)
                            .values(follow_up_analyses=follow_up_analyses)
                        )
                    else:
                        print(
                            "Could not find parent analysis with id: ",
                            parent_analysis_id,
                        )

    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not create a new analysis."
        new_analysis_data = None
    finally:
        return err, new_analysis_data


def get_analysis_data(analysis_id):
    try:
        err = None
        analysis_data = {}

        if analysis_id == "" or not analysis_id:
            print(analysis_id == "")
            print(analysis_id is None)
            print(not analysis_id)
            err = "Could not find analyis. Are you sure you have the correct link?"

        elif analysis_id != "" and analysis_id is not None and analysis_id != "new":
            print("Looking for uuid: ", analysis_id)
            # try to fetch analysis_data data
            with engine.begin() as conn:
                row = conn.execute(
                    select(Analyses).where(Analyses.analysis_id == analysis_id)
                ).fetchone()

                if row:
                    print("Found uuid: ", analysis_id)
                    analysis_data = analysis_data_from_row(row)
                else:
                    err = "Could not find analyis. Are you sure you have the correct link?"

    except Exception as e:
        err = "Server error. Please contact us."
        analysis_data = None
        print(e)
        traceback.print_exc()

    finally:
        return err, analysis_data


def get_assignment_understanding(analysis_id):
    """
    Returns the assignment_understanding column from the analysis with the given analysis_id
    """

    try:
        err = None
        understanding = None

        if analysis_id == "" or not analysis_id:
            err = "Could not find analyis. Are you sure you have the correct link?"

        elif analysis_id != "" and analysis_id is not None and analysis_id != "new":
            # try to fetch analysis_data data
            with engine.begin() as conn:
                row = conn.execute(
                    select(
                        Analyses.__table__.columns["assignment_understanding"]
                    ).where(Analyses.analysis_id == analysis_id)
                ).fetchone()

                if row:
                    understanding = row.assignment_understanding
                else:
                    err = "Could not find analyis. Are you sure you have the correct link?"

    except Exception as e:
        err = "Server error."
        understanding = None
        print(e)
        traceback.print_exc()
    finally:
        return err, understanding


def update_assignment_understanding(analysis_id, understanding):
    """
    Updates the assignment_understanding column in the analysis with the given analysis_id
    """

    try:
        err = None

        if analysis_id == "" or not analysis_id:
            err = "Could not find analyis. Are you sure you have the correct link?"

        elif analysis_id != "" and analysis_id is not None and analysis_id != "new":
            # try to fetch analysis_data data
            with engine.begin() as conn:
                conn.execute(
                    update(Analyses)
                    .where(Analyses.analysis_id == analysis_id)
                    .values(assignment_understanding=understanding)
                )

    except Exception as e:
        err = "Server error."
        print(e)
        traceback.print_exc()
    finally:
        return err


async def update_analysis_data(
    analysis_id, request_type=None, new_data=None, replace=False, overwrite_key=None
):
    err = None
    request_types = [
        "clarify",
        "understand",
        "gen_approaches",
        "gen_steps",
        "gen_analysis",
        "user_question",
    ]
    try:
        # if new data is a list, filter out null elements
        # this can sometimes happen when the LLM server takes too long to respond etc.
        if type(new_data) == list:
            new_data = list(filter(None, new_data))

        if request_type is None or request_type not in request_types:
            err = "Incorrect request_type: " + request_type

        else:
            with engine.begin() as conn:
                # first get the data
                row = conn.execute(
                    select(Analyses.__table__.columns[request_type]).where(
                        Analyses.analysis_id == analysis_id
                    )
                ).fetchone()

                if row:
                    curr_data = getattr(row, request_type) or []
                    print("current data length ", len(curr_data))

                    # if new data is a list and we're not asked to replace, concat
                    # if new data is anything else, replace
                    if (
                        type(new_data) == list or type(new_data) == YieldList
                    ) and not replace:
                        if not overwrite_key or type(overwrite_key) != str:
                            curr_data = curr_data + new_data
                        # if there's an overwrite_key provided,
                        # then go through old data, and the new_data
                        # if the overwrite_key is found in the old data, replace it with the elements that exist new_data with the same overwrite_key
                        # if it's not found, just append the item to the end
                        else:
                            print(
                                "Overwriting data with overwrite_key: ", overwrite_key
                            )
                            replaced = 0
                            for i, item in enumerate(new_data):
                                # try to find the item
                                found = False
                                for j, old_item in enumerate(curr_data):
                                    if old_item.get(overwrite_key) == item.get(
                                        overwrite_key
                                    ):
                                        curr_data[j] = item
                                        found = True
                                        replaced += 1
                                        break
                                if not found:
                                    # just append
                                    logging.info("Item not found. Appending.")
                                    curr_data.append(item)

                            print(
                                f"Replaced {replaced} items in {request_type} with overwrite_key: {overwrite_key}"
                            )
                            print(
                                "New length of ", request_type, " is ", len(curr_data)
                            )
                    else:
                        curr_data = new_data
                    print("writing to ", request_type, "in analyis id: ", analysis_id)
                    print("writing array of length: ", len(curr_data))
                    # insert back into analyses table
                    # if the request type is user_question, we will also update the embedding
                    if request_type == "user_question":
                        conn.execute(
                            update(Analyses)
                            .where(Analyses.analysis_id == analysis_id)
                            .values({request_type: new_data})
                        )
                    else:
                        conn.execute(
                            update(Analyses)
                            .where(Analyses.analysis_id == analysis_id)
                            .values({request_type: curr_data})
                        )
                else:
                    err = "Analysis not found."
                    raise ValueError(err)

    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


def analysis_data_from_row(row):
    rpt = None
    try:
        clarify = None if row.clarify is None else row.clarify
        gen_steps = None if row.gen_steps is None else row.gen_steps
        parent_analyses = row.parent_analyses or []
        follow_up_analyses = row.follow_up_analyses or []
        direct_parent_id = row.direct_parent_id or None

        # send only the ones that are not none.
        # we should have a better solution to this.
        rpt = {
            "user_question": row.user_question,
            "analysis_id": row.analysis_id,
            "timestamp": row.timestamp,
            "parent_analyses": parent_analyses,
            "follow_up_analyses": follow_up_analyses,
            "direct_parent_id": direct_parent_id,
        }

        if clarify is not None:
            rpt["clarify"] = {
                "success": True,
                "clarification_questions": clarify,
            }

        if gen_steps is not None:
            rpt["gen_steps"] = {
                "success": True,
                "steps": gen_steps,
            }

    except Exception as e:
        print(e)
        traceback.print_exc()
        rpt = None
    finally:
        return rpt


def get_all_analyses(api_key: str):
    # get analyses from the analyses table
    err = None
    analyses = []
    try:
        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(Analyses).where(Analyses.api_key == api_key)
            ).fetchall()
            if len(rows) > 0:
                # reshape with "success = true"
                for row in rows:
                    rpt = analysis_data_from_row(row)
                    if rpt is not None:
                        analyses.append(rpt)
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = "Something went wrong while fetching your analyses. Please contact us."
        analyses = None
    finally:
        return err, analyses


async def add_to_recently_viewed_docs(token, doc_id, timestamp, api_key):
    username = validate_user(token, get_username=True)
    if not username:
        return "Invalid token."
    try:
        print("Adding to recently viewed docs for user: ", username)
        with engine.begin() as conn:
            # add to recently accessed documents for this username
            # check if it exists
            row = conn.execute(
                select(RecentlyViewedDocs)
                .where(RecentlyViewedDocs.username == username)
                .where(RecentlyViewedDocs.api_key == api_key)
            ).fetchone()

            if row:
                print("Adding to recently viewed docs for user: ", username)
                # get the recent_docs array
                recent_docs = row.recent_docs or []
                # recent_docs is an array of arrays
                # each item is a [doc_id, timestamp]
                # check if doc_id is already in the array
                # if it is, update the timestamp
                # if not, add it to the array
                found = False
                for i, doc in enumerate(recent_docs):
                    if doc[0] == doc_id:
                        recent_docs[i][1] = timestamp
                        found = True
                        break

                if not found:
                    recent_docs.append([doc_id, timestamp])

                # update the row
                conn.execute(
                    update(RecentlyViewedDocs)
                    .where(RecentlyViewedDocs.username == username)
                    .where(RecentlyViewedDocs.api_key == api_key)
                    .values(recent_docs=recent_docs)
                )
            else:
                # create a new row
                conn.execute(
                    insert(RecentlyViewedDocs).values(
                        {
                            "api_key": api_key,
                            "username": username,
                            "recent_docs": [[doc_id, timestamp]],
                        }
                    )
                )
    except Exception as e:
        print(e)
        # traceback.print_exc()
        print("Could not add to recently viewed docs\n")


async def get_doc_data(api_key, doc_id, token, col_name="doc_blocks"):
    username = validate_user(token, get_username=True)
    if not username:
        return "Invalid token.", None
    err = None
    timestamp = str(datetime.datetime.now())
    doc_data = None

    try:
        """Find the document with the id in the Docs table.
        If it doesn't exist, create one and return empty data."""
        with engine.begin() as conn:
            # check if document exists
            row = conn.execute(select(Docs).where(Docs.doc_id == doc_id)).fetchone()

            if row:
                # document exists
                print("Found document with id: ", doc_id)
                doc_data = {
                    "doc_id": row.doc_id,
                    col_name: getattr(row, col_name),
                }

            else:
                # create a new document
                print("Creating new document with id: ", doc_id)
                doc_data = {
                    "doc_id": doc_id,
                    "doc_blocks": None,
                    "doc_xml": None,
                    "doc_uint8": None,
                    "username": username,
                }

                conn.execute(
                    insert(Docs).values(
                        {
                            "doc_id": doc_id,
                            "api_key": api_key,
                            "doc_blocks": None,
                            "doc_xml": None,
                            "doc_uint8": None,
                            "timestamp": timestamp,
                            "username": username,
                        }
                    )
                )

    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not create a new analysis."
        doc_data = None
    finally:
        return err, doc_data


async def delete_doc(doc_id):
    err = None
    try:
        with engine.begin() as conn:
            result = conn.execute(delete(Docs).where(Docs.doc_id == doc_id))

            if result.rowcount > 0:
                print("Deleted doc with id: ", doc_id)
            else:
                err = "Doc not found."
                raise ValueError(err)
    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


async def update_doc_data(doc_id, col_names=[], new_data={}):
    err = None
    if len(col_names) == 0 and len(new_data) == 0:
        return None

    try:
        with engine.begin() as conn:
            # first get the data
            row = conn.execute(
                select(*[Docs.__table__.columns[c] for c in col_names]).where(
                    Docs.doc_id == doc_id
                )
            ).fetchone()

            if row:
                print("Updating document with id: ", doc_id, "column: ", col_names)
                conn.execute(update(Docs).where(Docs.doc_id == doc_id).values(new_data))
            else:
                err = "Doc not found."
                raise ValueError(err)
    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


def create_table_chart(table_data):
    err = None
    if table_data is None or table_data.get("table_id") is None:
        return "Invalid table data"

    try:
        with engine.begin() as conn:
            print("Creating new table chart with id: ", table_data.get("table_id"))
            conn.execute(insert(TableCharts).values(table_data))

    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


async def update_table_chart_data(table_id, edited_table_data):
    err = None
    analysis = None
    updated_data = None

    if table_id is None:
        return "Invalid table data"

    try:
        with engine.begin() as conn:
            # check if exists.
            # if not, create
            row = conn.execute(
                select(TableCharts).where(TableCharts.table_id == table_id)
            ).fetchone()

            if not row:
                err = "Invalid table id"
            else:
                # print(edited_table_data)
                print("Running table again...")

                # execute the new code
                err, analysis, updated_data = await execute_code(
                    edited_table_data["code"]
                )

                if err is None:
                    chart_images = []
                    if hasattr(updated_data, "kmc_plot_paths"):
                        chart_images = [
                            {"path": kmc_path, "type": "kmc"}
                            for kmc_path in updated_data.kmc_plot_paths
                        ]

                    updated_data = {
                        "data_csv": updated_data.to_csv(
                            float_format="%.3f", index=False
                        ),
                        "sql": edited_table_data.get("sql"),
                        "code": edited_table_data.get("code"),
                        "tool": edited_table_data.get("tool"),
                        "reactive_vars": (
                            updated_data.reactive_vars
                            if hasattr(updated_data, "reactive_vars")
                            else None
                        ),
                        "table_id": table_id,
                        "chart_images": chart_images,
                        "error": None,
                    }

                    # insert the data back into TableCharts table
                    print("writing to table chart, table id: ", table_id)
                    updated_data["edited"] = True

                    conn.execute(
                        update(TableCharts)
                        .where(TableCharts.table_id == table_id)
                        .values(updated_data)
                    )
                else:
                    print("Error: ", err)
    except Exception as e:
        err = str(e)
        analysis = None
        updated_data = None
        print(e)
        traceback.print_exc()
    finally:
        return err, analysis, updated_data


async def get_table_data(table_id):
    err = None
    table_data = None
    if table_id == "" or table_id is None or not table_id:
        return "Invalid table data", None

    try:
        with engine.begin() as conn:
            # check if document exists
            row = conn.execute(
                select(TableCharts).where(TableCharts.table_id == table_id)
            ).fetchone()

            if row:
                # document exists
                print("Found table with id: ", table_id)
                table_data = row._mapping

            else:
                err = "Table not found."

    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not find table."
        table_data = None
    finally:
        return err, table_data


async def get_all_docs(token):
    username = validate_user(token, get_username=True)
    if not username:
        return "Invalid token.", None, None
    # get analyses from the analyses table
    err = None
    own_docs = []
    recently_viewed_docs = []
    try:
        """Get docs for a user from the defog_docs table"""
        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(
                    Docs.__table__.columns["doc_id"],
                    Docs.__table__.columns["doc_title"],
                    Docs.__table__.columns["doc_uint8"],
                    Docs.__table__.columns["timestamp"],
                    Docs.__table__.columns["archived"],
                ).where(Docs.username == username)
            ).fetchall()
            if len(rows) > 0:
                for row in rows:
                    doc = row._mapping
                    own_docs.append(doc)

        # get recently viewed docs
        with engine.begin() as conn:
            # first get the data
            # merge recentlyvieweddocs with docs to get the user_question too
            # create an array of objects with doc_id, doc_title, timestamp, user_question
            rows = conn.execute(
                select(
                    RecentlyViewedDocs.__table__.columns["recent_docs"],
                ).where(RecentlyViewedDocs.username == username)
            ).fetchall()

            if len(rows) > 0:
                for row in rows:
                    doc = row._mapping
                    for recent_doc in doc["recent_docs"]:
                        # get the doc data from the docs table
                        # this will skip docs that have been deleted because of the where clause
                        match = conn.execute(
                            select(
                                Docs.__table__.columns["doc_id"],
                                Docs.__table__.columns["doc_title"],
                                Docs.__table__.columns["timestamp"],
                                Docs.__table__.columns["username"],
                            ).where(Docs.doc_id == recent_doc[0])
                        ).fetchone()

                        if match:
                            recently_viewed_docs.append(
                                {
                                    "doc_id": match.doc_id,
                                    "doc_title": match.doc_title,
                                    # also return user who created this document
                                    "username": match.username,
                                    "timestamp": recent_doc[1],
                                }
                            )

    except Exception as e:
        print(e)
        traceback.print_exc()
        err = "Something went wrong while fetching your documents. Please contact us."
        own_docs = None
        recently_viewed_docs = None
    finally:
        return err, own_docs, recently_viewed_docs


async def get_all_analyses(api_key: str):
    # get analyses from the analyses table
    err = None
    analyses = []
    try:
        """Create a new analyis in the defog_analyses table"""
        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(
                    *[
                        Analyses.__table__.columns["analysis_id"],
                        Analyses.__table__.columns["user_question"],
                    ]
                )
                .where(Analyses.api_key == api_key)
                .where(Analyses.analysis_id.contains("analysis"))
            ).fetchall()

            if len(rows) > 0:
                for row in rows:
                    analyses.append(row._mapping)
    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not find analyses for the user."
        analyses = []
    finally:
        return err, analyses


def get_multiple_analyses(analysis_ids=[], columns=["analysis_id", "user_question"]):
    err = None
    analyses = []
    try:
        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(
                    *[
                        Analyses.__table__.columns[c]
                        for c in columns
                        if c in Analyses.__table__.columns
                    ]
                ).where(Analyses.analysis_id.in_(analysis_ids))
            ).fetchall()

            if len(rows) > 0:
                for row in rows:
                    analyses.append(row._mapping)
    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not find analyses for the user."
        analyses = []
    finally:
        return err, analyses


async def store_feedback(
    api_key,
    user_question,
    analysis_id,
    is_correct,
    comments,
    db_type,
):
    error = None
    did_overwrite = False

    asyncio.create_task(
        make_request(
            f"{os.environ.get('DEFOG_BASE_URL', 'https://api.defog.ai')}/update_agent_feedback",
            {
                "api_key": api_key,
                "user_question": user_question,
                "analysis_id": analysis_id,
                "is_correct": is_correct,
                "comments": comments,
                "db_type": db_type,
            },
        )
    )

    return error, did_overwrite


def get_all_tools():
    err = None
    tools = {}
    try:
        with engine.begin() as conn:
            all_tools = conn.execute(select(Tools)).fetchall()
            # convert this to a dictionary without embedding
            all_tools = {
                tool.function_name: {
                    "tool_name": tool.tool_name,
                    "function_name": tool.function_name,
                    "description": tool.description,
                    "code": tool.code,
                    "input_metadata": tool.input_metadata,
                    "output_metadata": tool.output_metadata,
                    "cannot_delete": tool.cannot_delete,
                    "cannot_disable": tool.cannot_disable,
                    "disabled": tool.disabled,
                }
                for tool in all_tools
            }

            # if user_question_embedding is None, return all tools
            tools = all_tools

    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
        tools = []
    finally:
        return err, tools


async def check_tool_exists(tool_name):
    err = None
    exists = False
    row = None
    try:
        with engine.begin() as conn:
            row = conn.execute(
                select(Tools).where(Tools.tool_name == tool_name)
            ).fetchone()
            if row:
                exists = True
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err, exists, row


async def add_tool(
    api_key,
    tool_name,
    function_name,
    description,
    code,
    input_metadata,
    output_metadata,
    cannot_delete=False,
    cannot_disable=False,
    replace_if_exists=True,
):
    err = None
    try:
        embedding = None
        # insert into the tools table
        with engine.begin() as conn:
            # first check if it exists
            err, exists, existing_tool = await check_tool_exists(tool_name)
            if err:
                raise Exception(err)

        no_changes = False
        if exists and existing_tool:
            # if this exists, and we're allowed to replace the tool
            # check if latest tool code is same as the code we are trying to insert
            # if we're not allowed to replace, raise an error
            if not replace_if_exists:
                raise ValueError(f"Tool {tool_name} already exists.")

            no_changes = existing_tool.code == code

        if no_changes:
            print(f"Tool {tool_name} already exists and no code changes detected.")
        else:
            print(f"Adding tool {function_name} to local postgres database.")
            with engine.begin() as conn:
                # delete if exists
                if existing_tool:
                    conn.execute(delete(Tools).where(Tools.tool_name == tool_name))

                # update with latest
                conn.execute(
                    insert(Tools).values(
                        {
                            "tool_name": tool_name,
                            "function_name": function_name,
                            "description": description,
                            "code": code,
                            # we don't use toolboxes anymore
                            # this defaults to None so no need to set it
                            # "toolbox": toolbox,
                            "input_metadata": input_metadata,
                            "output_metadata": output_metadata,
                            "cannot_delete": cannot_delete,
                            "cannot_disable": cannot_disable,
                            "disabled": False,
                        }
                    )
                )

        print(f"Adding tool {function_name} to the defog API server")
        asyncio.create_task(
            make_request(
                url=f"{os.environ.get('DEFOG_BASE_URL', 'https://api.defog.ai')}/update_tool",
                data={
                    "api_key": api_key,
                    "tool_name": tool_name,
                    "function_name": function_name,
                    "description": description,
                    "code": code,
                    "embedding": embedding,
                    "input_metadata": input_metadata,
                    "output_metadata": output_metadata,
                    # we don't use toolboxes anymore
                    # this defaults to None so no need to set it
                    # "toolbox": toolbox,
                    "disabled": False,
                    "cannot_delete": cannot_delete,
                    "cannot_disable": cannot_disable,
                },
            )
        )
    except ValueError as e:
        err = str(e)
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def update_tool(function_name, update_dict):
    err = None
    try:
        with engine.begin() as conn:
            # check if tool exists
            row = conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            ).fetchone()

            if row is None:
                raise ValueError(f"Tool {function_name} does not exist.")
            else:
                # update with latest
                conn.execute(
                    update(Tools)
                    .where(Tools.function_name == function_name)
                    .values(update_dict)
                )
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def toggle_disable_tool(function_name):
    err = None
    try:
        with engine.begin() as conn:
            # check cannot_disable
            rows = conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            ).fetchone()
            if rows is None:
                raise ValueError(f"Tool {function_name} does not exist.")
            elif rows.cannot_disable:
                raise ValueError(
                    f"Tool {function_name} cannot be disabled. Please contact admin."
                )
            else:
                conn.execute(
                    update(Tools)
                    .where(Tools.function_name == function_name)
                    .values(disabled=not rows.disabled)
                )
                print(
                    "Toggled tool: ", function_name, "to disabled: ", not rows.disabled
                )
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def delete_tool(function_name):
    err = None
    try:
        with engine.begin() as conn:
            # also cannot_delete check
            rows = conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            ).fetchone()
            if rows is None:
                raise ValueError(f"Tool {function_name} does not exist.")
            # elif rows.cannot_delete:
            #     raise ValueError(
            #         f"Tool {function_name} cannot be deleted. Please contact admin."
            #     )
            else:
                conn.execute(delete(Tools).where(Tools.function_name == function_name))
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def delete_all_tools():
    err = None
    try:
        with engine.begin() as conn:
            conn.execute(delete(Tools))
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def get_analysis_versions(root_analysis_id):
    # get all versions of an analysis
    # get ids that end with -v1, -v2, -v3..
    err = None
    versions = []
    try:
        with engine.begin() as conn:
            cursor = conn.connection.cursor()
            cursor.execute(
                """
                SELECT analysis_id, user_question, gen_steps
                FROM defog_analyses
                WHERE root_analysis_id = ?
                ORDER BY timestamp ASC
                """,
                (root_analysis_id,),
            )
            rows = cursor.fetchall()
            versions = [{"analysis_id": x[0], "user_question": x[1]} for x in rows]
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err, versions


# returns all combined user_questions of root_analysis + max_n direct parents
# helps embed tools better
async def get_analysis_question_context(analysis_id, max_n=5):
    # get this analysis
    # check direct_parent_id of this analysis
    # and keep going up the analysis chain till we get an is_root_analysis or we reach max_n
    # and finally also get the root_analysis_id from this analysis
    # and merge all the question: root analysis's plus all parents we found
    err = None
    question_context = ""
    try:
        curr_analysis_id = analysis_id

        count = 0
        while True:
            # get this analysis
            err, analysis_data = get_analysis_data(curr_analysis_id)
            if err:
                raise Exception(err)

            if analysis_data["direct_parent_id"] and count <= max_n:
                curr_analysis_id = analysis_data["direct_parent_id"]
                count += 1

                # skip if analysis was not fully completed
                # aka has no steps
                if (
                    not analysis_data["gen_steps"]
                    or len(analysis_data["gen_steps"]) == 0
                ):
                    continue

                # else add this q to context
                question_context = (
                    analysis_data["user_question"] + " " + question_context
                )
            else:
                break

    except Exception as e:
        err = str(e)[:300]
        question_context = ""
    finally:
        return err, question_context
