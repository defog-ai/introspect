import asyncio
from datetime import datetime
import logging
import os
import traceback
import uuid
from typing import Dict, Tuple

import redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm.attributes import flag_modified
from oracle.constants import TaskStage
from generic_utils import make_request
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    Text,
    create_engine,
    delete,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import declarative_base
from utils_logging import LOGGER

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
TEMP_TABLES_DBNAME = os.environ.get("TEMP_TABLES_DBNAME", "temp_tables")

ORACLE_ENABLED: bool = os.environ.get("ORACLE_ENABLED", "no") == "yes"
LOGGER.info(f"ORACLE_ENABLED: {ORACLE_ENABLED}")

if INTERNAL_DB == "sqlite":
    print("using sqlite as our internal db")
    # if using sqlite
    connection_uri = "sqlite:///defog_local.db"
    engine = create_engine(connection_uri, connect_args={"timeout": 3})
    if ORACLE_ENABLED:
        imported_tables_engine = create_engine(
            f"sqlite:///{IMPORTED_TABLES_DBNAME}.db", connect_args={"timeout": 3}
        )
        LOGGER.info(
            f"Created imported tables engine for sqlite: {imported_tables_engine}"
        )
        temp_tables_engine = create_engine(
            f"sqlite:///{TEMP_TABLES_DBNAME}.db", connect_args={"timeout": 3}
        )
        LOGGER.info(f"Created temp tables engine for sqlite: {temp_tables_engine}")
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
    connection_uri = f"postgresql+asyncpg://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
    engine = create_async_engine(connection_uri, pool_size=30)

    if ORACLE_ENABLED:
        if IMPORTED_TABLES_DBNAME == db_creds["database"]:
            print(
                f"IMPORTED_TABLES_DBNAME is the same as the main database: {IMPORTED_TABLES_DBNAME}. Consider use a different database name."
            )
        imported_tables_engine = create_engine(
            f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{IMPORTED_TABLES_DBNAME}"
        )
        LOGGER.info(
            f"Created imported tables engine for postgres: {imported_tables_engine}"
        )
        temp_tables_engine = create_engine(
            f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{TEMP_TABLES_DBNAME}"
        )
        LOGGER.info(f"Created temp tables engine for postgres: {temp_tables_engine}")
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
    engine = create_async_engine(connection_uri)

    if ORACLE_ENABLED:
        if IMPORTED_TABLES_DBNAME == db_creds["database"]:
            print(
                f"IMPORTED_TABLES_DBNAME is the same as the main database: {IMPORTED_TABLES_DBNAME}. Consider using a different database name."
            )
        imported_tables_engine = create_engine(
            f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{IMPORTED_TABLES_DBNAME}?driver=ODBC+Driver+18+for+SQL+Server"
        )
        LOGGER.info(
            f"Created imported tables engine for sqlserver: {imported_tables_engine}"
        )
        temp_tables_engine = create_engine(
            f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{TEMP_TABLES_DBNAME}?driver=ODBC+Driver+18+for+SQL+Server"
        )
        LOGGER.info(f"Created temp tables engine for sqlserver: {temp_tables_engine}")

metadata = MetaData()

Base = declarative_base(metadata=metadata)


class Analyses(Base):
    __tablename__ = "defog_analyses"
    analysis_id = Column(Text, primary_key=True)
    api_key = Column(Text, nullable=False)
    email = Column(Text)
    timestamp = Column(DateTime)
    clarify = Column(JSON)
    assignment_understanding = Column(JSON)
    user_question = Column(Text)
    gen_steps = Column(JSON)
    follow_up_analyses = Column(JSON)
    parent_analyses = Column(JSON)
    is_root_analysis = Column(Boolean, default=True)
    root_analysis_id = Column(Text)
    direct_parent_id = Column(Text)
    username = Column(Text)


class TableCharts(Base):
    __tablename__ = "defog_table_charts"
    table_id = Column(Text, primary_key=True)
    data_csv = Column(JSON)
    query = Column(Text)
    chart_images = Column(JSON)
    sql = Column(Text)
    code = Column(Text)
    tool = Column(JSON)
    edited = Column(Integer)
    error = Column(Text)
    reactive_vars = Column(JSON)


class ToolRuns(Base):
    __tablename__ = "defog_tool_runs"
    tool_run_id = Column(Text, primary_key=True)
    step = Column(JSON)
    outputs = Column(JSON)
    tool_name = Column(Text)
    tool_run_details = Column(JSON)
    error_message = Column(Text)
    edited = Column(Integer)
    analysis_id = Column(Text)


class Tools(Base):
    __tablename__ = "defog_tools"
    tool_name = Column(Text, primary_key=True)
    function_name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    input_metadata = Column(JSON)
    output_metadata = Column(JSON)
    toolbox = Column(Text, default=None)
    disabled = Column(Boolean, default=False)
    cannot_delete = Column(Boolean, default=False)
    cannot_disable = Column(Boolean, default=False)


class Users(Base):
    __tablename__ = "defog_users"
    username = Column(Text, primary_key=True)
    hashed_password = Column(Text)
    token = Column(Text, nullable=False)
    user_type = Column(Text, nullable=False)
    created_at = Column(DateTime)


class PlansFeedback(Base):
    __tablename__ = "defog_plans_feedback"
    analysis_id = Column(Text, primary_key=True)
    api_key = Column(Text, nullable=False)
    user_question = Column(Text, nullable=False)
    username = Column(Text, nullable=False)
    comments = Column(JSON)
    is_correct = Column(Boolean, nullable=False)
    # metadata is a reserved attribute in sqlalchemy so we need to map it to a different variable name
    feedback_metadata = Column(Text, name="metadata", nullable=False)
    client_description = Column(Text)
    glossary = Column(Text)
    db_type = Column(Text, nullable=False)


class DbCreds(Base):
    __tablename__ = "defog_db_creds"
    api_key = Column(Text, primary_key=True)
    db_type = Column(Text)
    db_creds = Column(JSON)


class UserHistory(Base):
    __tablename__ = "defog_user_history"
    username = Column(Text, primary_key=True)
    history = Column(JSON)


if ORACLE_ENABLED:

    class OracleReports(Base):
        __tablename__ = "oracle_reports"
        report_id = Column(Integer, primary_key=True, autoincrement=True)
        report_name = Column(Text)
        status = Column(Text)
        created_ts = Column(DateTime)
        api_key = Column(Text)
        username = Column(Text)
        inputs = Column(JSON)
        outputs = Column(JSON)
        feedback = Column(Text)
        comments = Column(JSON, default=None)

    class OracleAnalyses(Base):
        __tablename__ = "oracle_analyses"
        api_key = Column(Text, primary_key=True)
        report_id = Column(Integer, primary_key=True)
        analysis_id = Column(Text, primary_key=True)
        status = Column(Text, default="pending")
        analysis_json = Column(JSON)
        mdx = Column(Text, default=None)

    class OracleClarifications(Base):
        __tablename__ = "oracle_clarifications"
        clarification_id = Column(Text, primary_key=True)
        report_id = Column(Text, primary_key=True)
        llm_question = Column(Text)
        user_response = Column(Text)
        created_ts = Column(DateTime)
        resolved_ts = Column(DateTime)

    class OracleSources(Base):
        __tablename__ = "oracle_sources"
        api_key = Column(Text, primary_key=True)
        link = Column(Text, primary_key=True)
        title = Column(Text)
        position = Column(Integer)
        source_type = Column(Text)
        attributes = Column(Text)
        snippet = Column(Text)
        text_parsed = Column(Text)
        text_summary = Column(Text)


# tables should already be created in create_sql_tables.py
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


if ORACLE_ENABLED:
    try:
        ImportedTablesBase = automap_base()

        class ImportedTables(ImportedTablesBase):
            __tablename__ = "imported_tables"
            api_key = Column(Text, primary_key=True)
            table_link = Column(Text, primary_key=True)
            table_position = Column(Integer, primary_key=True)
            table_name = Column(Text)
            table_description = Column(Text)

        ImportedTablesBase.prepare(autoload_with=imported_tables_engine)
        ImportedTablesBase.classes.imported_tables = ImportedTables
    except Exception as e:
        LOGGER.debug(f"Error loading oracle tables: {e}")


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


async def get_db_type_creds(api_key: str) -> Tuple[str, Dict[str, str]]:
    async with engine.begin() as conn:
        row = await conn.execute(
            select(DbCreds.db_type, DbCreds.db_creds).where(DbCreds.api_key == api_key)
        )
        row = row.fetchone()
    return row


async def update_db_type_creds(api_key, db_type, db_creds):
    async with engine.begin() as conn:
        # first, check if the record exists
        record = await conn.execute(select(DbCreds).where(DbCreds.api_key == api_key))

        record = record.fetchone()

        if record:
            await conn.execute(
                update(DbCreds)
                .where(DbCreds.api_key == api_key)
                .values(db_type=db_type, db_creds=db_creds)
            )
        else:
            await conn.execute(
                insert(DbCreds).values(
                    api_key=api_key, db_type=db_type, db_creds=db_creds
                )
            )

    return True


async def validate_user(token, user_type=None, get_username=False):
    async with engine.begin() as conn:
        user = await conn.execute(select(Users).where(Users.hashed_password == token))
        user = user.fetchone()
    if user:
        if user_type == "admin":
            if user.user_type == "admin":
                if get_username:
                    return user.username
                else:
                    return True
            else:
                return False
        else:
            if get_username:
                return user.username
            else:
                return True
    else:
        return False


async def get_user_key_names(token):
    """
    Returns the key names that a user can access based on their token.
    If the user is an admin, they can access all the keys.
    If the user is not an admin, they can only access the keys in their allowed_dbs list.
    Returning `None` or an empty string means the user can access all keys.
    Returning "Invalid token" means the token is invalid.
    """
    async with engine.begin() as conn:
        user = await conn.execute(select(Users).where(Users.hashed_password == token))
        user = user.fetchone()

    if not user:
        return "Invalid token"

    # if user.user_type == "admin":
    return None

    # else:
    #     return user.allowed_dbs


async def initialise_analysis(
    user_question, token, api_key, custom_id=None, other_initialisation_details={}
):
    username = await validate_user(token, get_username=True)
    if not username:
        return "Invalid token.", None

    err = None
    timestamp = datetime.now()
    new_analysis_data = None

    try:
        """Create a new analyis in the defog_analyses table"""
        async with engine.begin() as conn:
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

            await conn.execute(insert(Analyses).values(new_analysis_data))
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
                    parent_analysis = await conn.execute(
                        select(Analyses).where(
                            Analyses.analysis_id == parent_analysis_id
                        )
                    )

                    parent_analysis = parent_analysis.fetchone()
                    if parent_analysis is not None:
                        parent_analysis = parent_analysis._mapping
                        # get the follow_up_analyses array
                        follow_up_analyses = (
                            parent_analysis.get("follow_up_analyses") or []
                        )
                        # add the analysis_id to the array
                        follow_up_analyses.append(analysis_id)
                        # update the row
                        await conn.execute(
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


async def get_analysis_data(analysis_id):
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
            async with engine.begin() as conn:
                row = await conn.execute(
                    select(Analyses).where(Analyses.analysis_id == analysis_id)
                )
                row = row.fetchone()

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


async def get_assignment_understanding(analysis_id):
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
            async with engine.begin() as conn:
                row = await conn.execute(
                    select(
                        Analyses.__table__.columns["assignment_understanding"]
                    ).where(Analyses.analysis_id == analysis_id)
                )

                row = row.fetchone()

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


async def update_assignment_understanding(analysis_id, understanding):
    """
    Updates the assignment_understanding column in the analysis with the given analysis_id
    """

    try:
        err = None

        if analysis_id == "" or not analysis_id:
            err = "Could not find analyis. Are you sure you have the correct link?"

        elif analysis_id != "" and analysis_id is not None and analysis_id != "new":
            # try to fetch analysis_data data
            async with engine.begin() as conn:
                await conn.execute(
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
            async with engine.begin() as conn:
                # first get the data
                row = await conn.execute(
                    select(Analyses.__table__.columns[request_type]).where(
                        Analyses.analysis_id == analysis_id
                    )
                )

                row = row.fetchone()

                if row:
                    curr_data = getattr(row, request_type) or []
                    print("current data length ", len(curr_data))

                    # if new data is a list and we're not asked to replace, concat
                    # if new data is anything else, replace
                    if (type(new_data) == list) and not replace:
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
                        await conn.execute(
                            update(Analyses)
                            .where(Analyses.analysis_id == analysis_id)
                            .values({request_type: new_data})
                        )
                    else:
                        await conn.execute(
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


async def get_all_analyses(api_key: str):
    # get analyses from the analyses table
    err = None
    analyses = []
    try:
        async with engine.begin() as conn:
            # first get the data
            rows = await conn.execute(
                select(Analyses).where(Analyses.api_key == api_key)
            )
            rows = rows.fetchall()
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


async def get_multiple_analyses(
    analysis_ids=[], columns=["analysis_id", "user_question"]
):
    err = None
    analyses = []
    try:
        async with engine.begin() as conn:
            # first get the data
            rows = await conn.execute(
                select(
                    *[
                        Analyses.__table__.columns[c]
                        for c in columns
                        if c in Analyses.__table__.columns
                    ]
                ).where(Analyses.analysis_id.in_(analysis_ids))
            )

            rows = rows.fetchall()

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


async def get_all_tools():
    err = None
    tools = {}
    try:
        async with engine.begin() as conn:
            all_tools = await conn.execute(select(Tools))

            all_tools = all_tools.fetchall()
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
        async with engine.begin() as conn:
            row = await conn.execute(select(Tools).where(Tools.tool_name == tool_name))
            row = row.fetchone()
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
        async with engine.begin() as conn:
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
            async with engine.begin() as conn:
                # delete if exists
                if existing_tool:
                    conn.execute(delete(Tools).where(Tools.tool_name == tool_name))

                # update with latest
                await conn.execute(
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
        async with engine.begin() as conn:
            # check if tool exists
            row = await conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            )
            row = row.fetchone()

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
        async with engine.begin() as conn:
            # check cannot_disable
            rows = await conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            )
            rows = rows.fetchone()
            if rows is None:
                raise ValueError(f"Tool {function_name} does not exist.")
            elif rows.cannot_disable:
                raise ValueError(
                    f"Tool {function_name} cannot be disabled. Please contact admin."
                )
            else:
                await conn.execute(
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
        async with engine.begin() as conn:
            # also cannot_delete check
            rows = await conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            )
            rows = rows.fetchone()
            if rows is None:
                raise ValueError(f"Tool {function_name} does not exist.")
            # elif rows.cannot_delete:
            #     raise ValueError(
            #         f"Tool {function_name} cannot be deleted. Please contact admin."
            #     )
            else:
                await conn.execute(
                    delete(Tools).where(Tools.function_name == function_name)
                )
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def delete_all_tools():
    err = None
    try:
        async with engine.begin() as conn:
            await conn.execute(delete(Tools))
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


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
            err, analysis_data = await get_analysis_data(curr_analysis_id)
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


async def update_status(report_id: int, new_status: str):
    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(OracleReports).where(OracleReports.report_id == report_id)
                result = await session.execute(stmt)
                report = result.scalar_one()
                report.status = new_status
    except Exception as e:
        LOGGER.error(f"Error updating status for report {report_id}: {str(e)}")


async def get_report_data(report_id: int, api_key: str):
    async with AsyncSession(engine) as session:
        stmt = select(OracleReports).where(
            OracleReports.api_key == api_key,
            OracleReports.report_id == report_id,
        )

        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row:
            report_data = {
                column.name: (
                    getattr(row, column.name).isoformat()
                    if isinstance(getattr(row, column.name), datetime)
                    else getattr(row, column.name)
                )
                for column in row.__table__.columns
            }
            return {"data": report_data}
        else:
            return {"error": "Report not found"}


async def delete_analysis(api_key: str, analysis_id: str, report_id: int):
    """
    Given an api_key, analysis_id and report_id, this endpoint will delete the analysis from the database in the oracle_analyses table.
    """

    err = None

    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = delete(OracleAnalyses).where(
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id,
                    OracleAnalyses.api_key == api_key,
                )
                await session.execute(stmt)
    except Exception as e:
        LOGGER.error(f"Error deleting analysis {analysis_id}: {str(e)}")
        err = str(e)[:300]
    finally:
        return err


async def add_or_update_analysis(
    api_key: str,
    analysis_id: str,
    report_id: int,
    analysis_json: Dict,
    status: str = "pending",
    mdx: str = None,
) -> str:
    """
    Given a report_id, this endpoint will add or (if it already exists) update the data for a particular analysis in the database in the oracle_analyses table.
    """
    err = None
    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                # if the analysis id exists, update it
                stmt = select(OracleAnalyses).where(
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id,
                    OracleAnalyses.api_key == api_key,
                )
                result = await session.execute(stmt)
                analysis = result.scalar_one_or_none()
                if analysis:
                    analysis.status = status
                    analysis.analysis_json = analysis_json
                    analysis.mdx = mdx
                else:
                    stmt = insert(OracleAnalyses).values(
                        report_id=report_id,
                        api_key=api_key,
                        analysis_id=analysis_id,
                        status=status,
                        analysis_json=analysis_json,
                        mdx=mdx,
                    )
                    await session.execute(stmt)
    except Exception as e:
        LOGGER.error(f"Error adding analysis {analysis_id}: {str(e)}")
        err = str(e)[:300]
    return err


async def get_analysis_status(api_key: str, analysis_id: str, report_id: int) -> str:
    """
    Given an api_key, analysis_id and report_id, this endpoint will return the status of the analysis.
    """

    err = None
    status = None

    try:
        async with AsyncSession(engine) as session:
            stmt = select(OracleAnalyses).where(
                OracleAnalyses.analysis_id == analysis_id,
                OracleAnalyses.report_id == report_id,
                OracleAnalyses.api_key == api_key,
            )

            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row:
                status = row.status
            else:
                raise Exception("Analysis not found")
    except Exception as e:
        LOGGER.error(f"Error getting analysis status {analysis_id}: {str(e)}")
        status = None
        err = str(e)[:300]
    finally:
        return err, status


async def update_analysis_status(
    api_key: str, analysis_id: str, report_id: int, new_status: str
):
    """
    Given an api_key, analysis_id and report_id, this endpoint will update the status of the analysis.
    If the analysis is not found, it will error.
    """

    err = None

    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(OracleAnalyses).where(
                    OracleAnalyses.analysis_id == analysis_id,
                    OracleAnalyses.report_id == report_id,
                    OracleAnalyses.api_key == api_key,
                )

                result = await session.execute(stmt)
                row = result.scalar_one_or_none()

                if row:
                    row.status = new_status
                else:
                    raise Exception("Analysis not found")
    except Exception as e:
        LOGGER.error(f"Error updating analysis status {analysis_id}: {str(e)}")
        err = str(e)[:300]
    finally:
        return err


async def update_summary_dict(api_key: str, report_id: int, summary_dict: Dict):
    """
    Given a report_id, this endpoint will update the summary_dict in the database in the oracle_reports table.
    Also updates the report_name if a title is present in the summary_dict.
    """

    err = None

    try:
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(OracleReports).where(
                    OracleReports.api_key == api_key, OracleReports.report_id == report_id
                )
                result = await session.execute(stmt)
                report = result.scalar_one_or_none()
                if report:
                    LOGGER.info(f"Updating summary dict for report {report_id}")

                    new_outputs = report.outputs
                    new_outputs[TaskStage.EXPORT.value]["executive_summary"] = summary_dict
                    report.outputs = new_outputs

                    # Update report title if present in summary_dict
                    title = summary_dict.get("title")
                    if title:
                        report.report_name = title

                    flag_modified(report, "outputs")
                else:
                    raise Exception("Report not found")
    except Exception as e:
        LOGGER.error(f"Error updating summary dict for report {report_id}: {str(e)}")
        err = str(e)[:300]
    finally:
        return err


async def update_report_name(report_id: int, report_name: str) -> None:
    """
    Updates the report_name for a given report_id in the oracle_reports table.

    Args:
        report_id: The ID of the report to update
        report_name: The new report name to set
    """

    async with AsyncSession(engine) as session:
        async with session.begin():
            stmt = select(OracleReports).where(OracleReports.report_id == report_id)
            result = await session.execute(stmt)
            report = result.scalar_one()
            report.report_name = report_name