# read a sql file, and create tables in sqlite database

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Float,
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
    Column("allowed_dbs", Text, nullable=True),
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
    Column("report_id", Integer, primary_key=True, autoincrement=True),
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

# Initialize Oracle MetaData object
imported_metadata = MetaData()

imported_tables = Table(
    "imported_tables",
    imported_metadata,
    Column("table_link", Text, primary_key=True),
    Column("table_position", Float, primary_key=True),
    Column("table_name", Text),
    Column("table_description", Text),
)


def add_column(engine, table_name, column):
    """
    This function explicitly adds a column to a table in the database.
    This is useful when the table already exists and you want to add a new column to it. For example, when you have released a new feature to Defog that requires that a new column be added to the database.
    """
    column_name = column.compile(dialect=engine.dialect)
    column_type = column.type.compile(engine.dialect)
    engine.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


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

    # do this only if oracle is enabled
    # check if the IMPORTED_TABLES_DBNAME exists in the database
    if os.environ.get("ORACLE_ENABLED", "no") == "yes":
        imported_tables_db = os.environ.get("IMPORTED_TABLES_DBNAME", "imported_tables")
        imported_connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{imported_tables_db}"

        imported_engine = create_engine(imported_connection_uri, echo=True)
        imported_metadata.create_all(imported_engine)


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

    # using sqlalchemy, check if the column `allowed_dbs` exists in the table `defog_users`
    # if not, add the column
    column_exists = True
    with engine.connect() as conn:
        result = conn.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = 'defog_users' AND column_name = 'allowed_dbs';"
        )
        if not result.fetchone():
            column_exists = False

    if not column_exists:
        add_column(engine, "defog_users", Column("allowed_dbs", Text, nullable=True))


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
