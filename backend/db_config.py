import os

import redis
import psycopg2
import pyodbc
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from utils_logging import LOGGER

REDIS_HOST = os.getenv("REDIS_INTERNAL_HOST", "agents-redis")
REDIS_PORT = os.getenv("REDIS_INTERNAL_PORT", 6379)
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)

INTERNAL_DB = os.environ.get("INTERNAL_DB", None)
IMPORTED_TABLES_DBNAME = os.environ.get("IMPORTED_TABLES_DBNAME", "imported_tables")
TEMP_TABLES_DBNAME = os.environ.get("TEMP_TABLES_DBNAME", "temp_tables")

def get_db_engine() -> tuple[AsyncEngine, Engine | None, Engine | None]:
    """
    Returns a tuple of the 
    - async engine for querying the user's database,
    - engine for querying the imported tables database, and
    - engine for querying the temp tables database.
    """
    if INTERNAL_DB == "sqlite":
        print("using sqlite as our internal db")
        connection_uri = "sqlite:///defog_local.db"
        engine = create_async_engine(connection_uri, connect_args={"timeout": 3})
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
        return engine, imported_tables_engine, temp_tables_engine

    elif INTERNAL_DB == "postgres":
        db_creds = {
            "user": os.environ.get("DBUSER", "postgres"),
            "password": os.environ.get("DBPASSWORD", "postgres"),
            "host": os.environ.get("DBHOST", "agents-postgres"),
            "port": os.environ.get("DBPORT", "5432"),
            "database": os.environ.get("DATABASE", "postgres"),
        }

        print("using postgres as our internal db")
        connection_uri = f"postgresql+asyncpg://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
        engine = create_async_engine(connection_uri, pool_size=30)

        if IMPORTED_TABLES_DBNAME == db_creds["database"]:
            print(
                f"IMPORTED_TABLES_DBNAME is the same as the main database: {IMPORTED_TABLES_DBNAME}. Consider use a different database name."
            )
        
        # Create databases using psycopg2 with autocommit
        conn = psycopg2.connect(
            dbname="postgres",
            user=db_creds["user"],
            password=db_creds["password"],
            host=db_creds["host"],
            port=db_creds["port"]
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Check and create IMPORTED_TABLES_DBNAME
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (IMPORTED_TABLES_DBNAME,))
        exists = cur.fetchone() is not None
        
        if not exists:
            # Terminate existing connections
            cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (IMPORTED_TABLES_DBNAME,))
            cur.execute(f"CREATE DATABASE {IMPORTED_TABLES_DBNAME}")
            LOGGER.info(f"Created database {IMPORTED_TABLES_DBNAME}")
        
        # Check and create TEMP_TABLES_DBNAME
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (TEMP_TABLES_DBNAME,))
        exists = cur.fetchone() is not None
        
        if not exists:
            cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (TEMP_TABLES_DBNAME,))
            cur.execute(f"CREATE DATABASE {TEMP_TABLES_DBNAME}")
            LOGGER.info(f"Created database {TEMP_TABLES_DBNAME}")
        
        cur.close()
        conn.close()

        imported_tables_engine = create_engine(
            f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{IMPORTED_TABLES_DBNAME}"
        )
        LOGGER.info(
            f"Created imported tables engine for postgres: {imported_tables_engine}"
        )
        temp_tables_engine = create_engine(
            f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{TEMP_TABLES_DBNAME}"
        )
        LOGGER.info(
            f"Created temp tables engine for postgres: {temp_tables_engine}"
        )
        return engine, imported_tables_engine, temp_tables_engine

    elif INTERNAL_DB == "sqlserver":
        db_creds = {
            "user": os.environ.get("DBUSER", "sa"),
            "password": os.environ.get("DBPASSWORD", "Password1"),
            "host": os.environ.get("DBHOST", "localhost"),
            "database": os.environ.get("DATABASE", "defog"),
            "port": os.environ.get("DBPORT", "1433"),
        }

        connection_uri = f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}?driver=ODBC+Driver+18+for+SQL+Server"
        engine = create_async_engine(connection_uri)

        if IMPORTED_TABLES_DBNAME == db_creds["database"]:
            print(
                f"IMPORTED_TABLES_DBNAME is the same as the main database: {IMPORTED_TABLES_DBNAME}. Consider using a different database name."
            )
        
        # Create databases using pyodbc directly
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={db_creds['host']},{db_creds['port']};DATABASE=master;UID={db_creds['user']};PWD={db_creds['password']}"
        conn = pyodbc.connect(conn_str, autocommit=True)
        cur = conn.cursor()

        # Check and create IMPORTED_TABLES_DBNAME
        cur.execute("SELECT 1 FROM sys.databases WHERE name = ?", (IMPORTED_TABLES_DBNAME,))
        exists = cur.fetchone() is not None
        
        if not exists:
            cur.execute(f"CREATE DATABASE {IMPORTED_TABLES_DBNAME}")
            LOGGER.info(f"Created database {IMPORTED_TABLES_DBNAME}")
        
        # Check and create TEMP_TABLES_DBNAME
        cur.execute("SELECT 1 FROM sys.databases WHERE name = ?", (TEMP_TABLES_DBNAME,))
        exists = cur.fetchone() is not None
        
        if not exists:
            cur.execute(f"CREATE DATABASE {TEMP_TABLES_DBNAME}")
            LOGGER.info(f"Created database {TEMP_TABLES_DBNAME}")
        
        cur.close()
        conn.close()

        imported_tables_engine = create_engine(
            f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{IMPORTED_TABLES_DBNAME}?driver=ODBC+Driver+18+for+SQL+Server"
        )
        LOGGER.info(
            f"Created imported tables engine for sqlserver: {imported_tables_engine}"
        )
        temp_tables_engine = create_engine(
            f"mssql+pyodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{TEMP_TABLES_DBNAME}?driver=ODBC+Driver+18+for+SQL+Server"
        )
        LOGGER.info(
            f"Created temp tables engine for sqlserver: {temp_tables_engine}"
        )
        return engine, imported_tables_engine, temp_tables_engine


engine, imported_tables_engine, temp_tables_engine = get_db_engine()
