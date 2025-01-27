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
    Column("clarify", JSON),
    Column("assignment_understanding", JSON),
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

defog_tools = Table(
    "defog_tools",
    metadata,
    Column("tool_name", Text, primary_key=True),
    Column("function_name", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("code", Text, nullable=False),
    Column("input_metadata", JSON),
    Column("output_metadata", JSON),
    # we're moving away from toolboxes
    # but don't want to cause unnecessary changes to pg tables.
    # so keeping this here anyway
    # with a default
    Column("toolbox", Text, default=None),
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
    Column("created_at", DateTime),
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

oracle_context = Table(
    "oracle_context",
    metadata,
    Column("api_key", Text, primary_key=True),
    Column("clarification_context", Text),
    Column("generate_questions_context", Text),
    Column("generate_questions_deeper_context", Text),
    Column("generate_report_context", Text),
)

oracle_reports = Table(
    "oracle_reports",
    metadata,
    Column("report_id", Integer, primary_key=True, autoincrement=True),
    Column("report_name", Text),
    Column("status", Text),
    Column("created_ts", DateTime),
    Column("api_key", Text),
    Column("username", Text),
    Column("inputs", JSON),
    Column("outputs", JSON),
    Column("feedback", Text),
    Column("general_comments", Text, default=None),
    Column("comments", JSON, default=None),
)

oracle_analyses = Table(
    "oracle_analyses",
    metadata,
    Column("api_key", Text, primary_key=True),
    Column("report_id", Integer, primary_key=True),
    Column("analysis_id", Text, primary_key=True),
    Column("status", Text, default="pending", nullable=True),
    Column("analysis_json", JSON, nullable=True),
    Column("mdx", Text, default=None, nullable=True),
)

oracle_sources = Table(
    "oracle_sources",
    metadata,
    Column("api_key", Text, primary_key=True),
    Column("link", Text, primary_key=True),
    Column("title", Text),
    Column("position", Integer),
    Column("source_type", Text),
    Column("attributes", Text),
    Column("snippet", Text),
    Column("text_parsed", Text),
    Column("text_summary", Text),
)

defog_user_history = Table(
    "defog_user_history",
    metadata,
    Column("username", Text, primary_key=True),
    Column("history", JSON),
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


def create_sqlserver_tables():
    """
    Create tables in SQL Server database
    """
    db_creds = {
        "user": os.environ.get("DBUSER", "sa"),
        "password": os.environ.get("DBPASSWORD", "Password1"),
        "host": os.environ.get("DBHOST", "localhost"),
        "database": os.environ.get("DATABASE", "defog"),
        "port": os.environ.get("DBPORT", "1433"),
    }

    # if using sqlserver
    connection_uri = f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}?driver=ODBC+Driver+18+for+SQL+Server"

    # Create an engine (SQL Server in this example)
    engine = create_engine(connection_uri, echo=True)

    # Create tables in the database
    metadata.create_all(engine)


# see from the command line arg if we are creating tables in sqlite or postgres
if __name__ == "__main__":
    internal_db = os.getenv("INTERNAL_DB", "postgres")

    if internal_db == "sqlite":
        create_sqlite_tables()
    elif internal_db == "postgres":
        create_postgres_tables()
    elif internal_db == "sqlserver":
        create_sqlserver_tables()
    else:
        raise ValueError("Invalid db_type")
