# read a sql file, and create tables in sqlite database

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    Boolean,
    DateTime,
)
from sqlalchemy.dialects.sqlite import JSON
import os

# Initialize MetaData object
metadata = MetaData()

# Define tables
defog_docs = Table(
    "defog_docs",
    metadata,
    Column("doc_id", Text, primary_key=True),
    Column("doc_md", Text),
    Column("doc_blocks", JSON),
    Column("editor_defog_blocks", JSON),
    Column("api_key", Text, nullable=False),
    Column("timestamp", DateTime),
    Column("username", Text),
    Column("doc_xml", Text),
    Column("doc_uint8", JSON),
    Column("doc_title", Text),
    Column("archived", Boolean, default=False),
)

defog_recently_viewed_docs = Table(
    "defog_recently_viewed_docs",
    metadata,
    Column("username", Text, primary_key=True),
    Column("api_key", Text, nullable=False),
    Column("recent_docs", JSON),
)

defog_analyses = Table(
    "defog_analyses",
    metadata,
    Column("analysis_id", Text, primary_key=True),
    Column("api_key", Text, nullable=False),
    Column("email", Text),
    Column("timestamp", DateTime),
    Column("approaches", JSON),
    Column("clarify", JSON),
    Column("assignment_understanding", JSON),
    Column("understand", JSON),
    Column("gen_approaches", JSON),
    Column("user_question", Text),
    Column("gen_steps", JSON),
    Column("follow_up_analyses", JSON),
    Column("parent_analyses", JSON),
    Column("is_root_analysis", Boolean, default=True),
    Column("root_analysis_id", Text),
    Column("direct_parent_id", Text),
    Column("username", Text),
)

defog_table_charts = Table(
    "defog_table_charts",
    metadata,
    Column("table_id", Text, primary_key=True),
    Column("data_csv", JSON),
    Column("query", Text),
    Column("chart_images", JSON),
    Column("sql", Text),
    Column("code", Text),
    Column("tool", JSON),
    Column("edited", Integer),
    Column("error", Text),
    Column("reactive_vars", JSON),
)

defog_tool_runs = Table(
    "defog_tool_runs",
    metadata,
    Column("tool_run_id", Text, primary_key=True),
    Column("step", JSON),
    Column("outputs", JSON),
    Column("tool_name", Text),
    Column("tool_run_details", JSON),
    Column("error_message", Text),
    Column("edited", Integer),
    Column("analysis_id", Text),
)

defog_toolboxes = Table(
    "defog_toolboxes",
    metadata,
    Column("api_key", Text, primary_key=True),
    Column("username", Text, nullable=False),
    Column("toolboxes", JSON),
)

defog_tools = Table(
    "defog_tools",
    metadata,
    Column("tool_name", Text, primary_key=True),
    Column("function_name", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("code", Text, nullable=False),
    Column("input_metadata", JSON),
    Column("output_metadata", JSON),
    Column("toolbox", Text),
    Column("disabled", Boolean, default=False),
    Column("cannot_delete", Boolean, default=False),
    Column("cannot_disable", Boolean, default=False),
)

defog_users = Table(
    "defog_users",
    metadata,
    Column("username", Text, primary_key=True),
    Column("hashed_password", Text),
    Column("token", Text, nullable=False),
    Column("user_type", Text, nullable=False),
    Column("csv_tables", Text),
    Column("is_premium", Boolean),
    Column("created_at", DateTime),
    Column("is_verified", Boolean),
)

defog_plans_feedback = Table(
    "defog_plans_feedback",
    metadata,
    Column("analysis_id", Text, primary_key=True),
    Column("api_key", Text, nullable=False),
    Column("user_question", Text, nullable=False),
    Column("username", Text, nullable=False),
    Column("comments", JSON),
    Column("is_correct", Boolean, nullable=False),
    Column("metadata", Text, nullable=False),
    Column("client_description", Text),
    Column("glossary", Text),
    Column("db_type", Text, nullable=False),
)

defog_db_creds = Table(
    "defog_db_creds",
    metadata,
    Column("api_key", Text, primary_key=True),
    Column("db_type", Text),
    Column("db_creds", JSON),
)

oracle_reports = Table(
    "oracle_reports",
    metadata,
    Column("report_id", Text, primary_key=True),
    Column("report_name", Text),
    Column("status", Text),
    Column("created_ts", DateTime),
    Column("api_key", Text),
    Column("username", Text),
    Column("inputs", JSON),
    Column("outputs", JSON),
    Column("feedback", Text),
)

oracle_clarifications = Table(
    "oracle_clarifications",
    metadata,
    Column("clarification_id", Text, primary_key=True),
    Column("report_id", Text, primary_key=True),
    Column("llm_question", Text),
    Column("user_response", Text),
    Column("created_ts", DateTime),
    Column("resolved_ts", DateTime),
)

oracle_sources = Table(
    "oracle_sources",
    metadata,
    Column("link", Text, primary_key=True),
    Column("title", Text),
    Column("position", Integer),
    Column("source_type", Text),
    Column("attributes", Text),
    Column("snippet", Text),
    Column("text_parsed", Text),
    Column("text_summary", Text),
)


def create_sqlite_tables():
    """
    Create tables in SQLite database
    """
    path_to_sql_file = "defog_local.db"

    if not os.path.exists(path_to_sql_file):
        open(path_to_sql_file, "w").close()

    # Create an engine (SQLite in this example)
    engine = create_engine(f"sqlite:///{path_to_sql_file}", echo=True)

    # Create tables in the database
    metadata.create_all(engine)


def create_postgres_tables():
    """
    Create tables in Postgres database
    """
    db_creds = {
        "user": os.environ.get("DBUSER", "postgres"),
        "password": os.environ.get("DBPASSWORD", "postgres"),
        "host": os.environ.get("DBHOST", "agents-postgres"),
        "port": os.environ.get("DBPORT", "5432"),
        "database": os.environ.get("DATABASE", "postgres"),
    }

    # if using postgres
    connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"

    # Create an engine (Postgres in this example)
    engine = create_engine(connection_uri, echo=True)

    # Create tables in the database
    metadata.create_all(engine)


# see from the command line arg if we are creating tables in sqlite or postgres
if __name__ == "__main__":
    db_type = os.getenv("DB_TYPE", "sqlite")

    if db_type == "sqlite":
        create_sqlite_tables()
    elif db_type == "postgres":
        create_postgres_tables()
    else:
        raise ValueError("Invalid db_type")
