import os
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    text,
)

# Initialize Oracle MetaData object
imported_metadata = MetaData()

imported_tables = Table(
    "imported_tables",
    imported_metadata,
    Column("api_key", Text, primary_key=True),
    Column("table_link", Text, primary_key=True),
    Column("table_position", Integer, primary_key=True),
    Column("table_name", Text),
    Column("table_description", Text),
)

# do this only if oracle is enabled
if os.environ.get("ORACLE_ENABLED", "no") == "yes":
    imported_tables_db = os.environ.get("IMPORTED_TABLES_DBNAME", "imported_tables")
    temp_tables_db = os.environ.get("TEMP_TABLES_DBNAME", "temp_tables")

    db_creds = {
        "user": os.environ.get("DBUSER", "postgres"),
        "password": os.environ.get("DBPASSWORD", "postgres"),
        "host": os.environ.get("DBHOST", "agents-postgres"),
        "port": os.environ.get("DBPORT", "5432"),
        "database": os.environ.get("DATABASE", "postgres"),
    }

    # connect to the main database
    connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
    engine = create_engine(connection_uri, echo=True)

    with engine.connect() as conn:
        # check if the IMPORTED_TABLES_DBNAME database exists, if not create it
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{imported_tables_db}'")
        )
        if not result.fetchone():
            raw_conn = (
                engine.raw_connection()
            )  # use a raw connection to disable the transaction block
            try:
                raw_conn.set_isolation_level(0)  # Set autocommit mode
                with raw_conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE {imported_tables_db}")
                print(f"Created database {imported_tables_db}.")
            finally:
                raw_conn.close()
        # check if the TEMP_TABLES_DBNAME database exists, if not create it
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{temp_tables_db}'")
        )
        if not result.fetchone():
            raw_conn = engine.raw_connection()
            try:
                raw_conn.set_isolation_level(0)
                with raw_conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE {temp_tables_db}")
                print(f"Created database {temp_tables_db}.")
            finally:
                raw_conn.close()

    # create tables in the imported tables database
    imported_connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{imported_tables_db}"
    imported_engine = create_engine(imported_connection_uri, echo=True)
    imported_metadata.create_all(imported_engine)
