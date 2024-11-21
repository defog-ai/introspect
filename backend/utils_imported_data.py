import logging
from typing import List, Optional, Tuple

from sqlalchemy import (
    MetaData,
    Table,
    inspect as sql_inspect,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.schema import DropTable

from db_utils import (
    IMPORTED_TABLES_DBNAME,
    INTERNAL_DB,
    ImportedTables,
    imported_tables_engine,
)
from utils_df import mk_df
from utils_logging import LOG_LEVEL
import requests

IMPORTED_SCHEMA = "imported"  # schema name to store imported tables
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(LOG_LEVEL)


def is_pdf_url(url: str) -> bool:
    try:
        if not "http" in url:
            return False
        if "http" in url and ".pdf" in url:
            return True
        # else check if it's a webpage pointing to a pdf
        response = requests.head(url, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "")
        return content_type == "application/pdf"
    except requests.RequestException:
        return False


def get_source_type(link: str) -> str:
    if is_pdf_url(link):
        return "webpage-pdf"
    elif ".pdf" in link:
        return "pdf"
    elif "http" in link:
        return "webpage"
    else:
        LOGGER.error(f"Unknown source type for link: {link}")
        return "unknown"


def update_imported_tables_db(
    api_key: str,
    link: str,
    table_index: int,
    new_table_name: str,
    data: List[List[str]],
    schema_name: str,
) -> Tuple[bool, Optional[str]]:
    """
    Updates the IMPORTED_TABLES_DBNAME database with the new schema and table.
    Replaces table from IMPORTED_TABLES_DBNAME database if it already exists.
    data is a list of lists where the first list consists of the column names and the rest are the rows.
    This function should always precede `update_imported_tables` as it first retrieves the old table name if the
    table (defined by its link/index) already exists in the imported_tables table.
    """
    LOGGER.debug(
        f"Updating imported tables database with schema.table: `{schema_name}.{new_table_name}`"
    )
    # create schema in imported_tables db if it doesn't exist
    try:
        if INTERNAL_DB == "postgres":
            # check if schema exists
            inspector = sql_inspect(imported_tables_engine)
            schema_names = inspector.get_schema_names()
            schema_exists = schema_name in schema_names
            if not schema_exists:
                create_schema_stmt = f"CREATE SCHEMA {schema_name};"

                with imported_tables_engine.begin() as imported_tables_connection:
                    LOGGER.debug(
                        f"inside with connection. creating schema:\n{create_schema_stmt}"
                    )
                    imported_tables_connection.execute(text(create_schema_stmt))
                    LOGGER.info(
                        f"Created schema `{schema_name}` in {IMPORTED_TABLES_DBNAME} database."
                    )
        else:
            LOGGER.error(f"INTERNAL_DB is not postgres. Cannot create schema.")
            return False, None
    except Exception as e:
        LOGGER.error(
            f"Error creating schema `{schema_name}` in {IMPORTED_TABLES_DBNAME} database: {e}"
        )
        return False, None

    # check if link and table_index already exist in imported_tables table
    stmt = select(ImportedTables.table_name).where(
        ImportedTables.api_key == api_key,
        ImportedTables.table_link == link,
        ImportedTables.table_position == table_index,
    )

    try:
        with imported_tables_engine.begin() as imported_tables_connection:
            result = imported_tables_connection.execute(stmt)
            scalar_result = result.scalar()
    except Exception as e:
        LOGGER.error(
            f"Error occurred in checking if entry `{link}` in position `{table_index}` exists in imported_tables table: {e}"
        )
        return False, None

    if scalar_result is not None:
        LOGGER.info(
            f"Entry `{link}` in position `{table_index}` already exists in imported_tables table."
        )
        # get old table name without schema
        old_table_name = scalar_result.split(".")[-1]
        LOGGER.info(
            f"Previous table name: `{old_table_name}`, New table name:  `{new_table_name}`"
        )

        # drop old table name if it already exists in imported_tables database

        try:
            with imported_tables_engine.begin() as imported_tables_connection:
                inspector = sql_inspect(imported_tables_engine)
                table_exists = inspector.has_table(old_table_name, schema=schema_name)
                if table_exists:
                    table = Table(old_table_name, MetaData(), schema=schema_name)
                    drop_stmt = DropTable(table, if_exists=True)
                    imported_tables_connection.execute(drop_stmt)
                    LOGGER.info(
                        f"Dropped existing table `{old_table_name}` from {IMPORTED_TABLES_DBNAME} database, schema `{schema_name}`."
                    )
        except Exception as e:
            LOGGER.error(
                f"Error dropping existing table `{old_table_name}` from {IMPORTED_TABLES_DBNAME} database, schema `{schema_name}`: {e}"
            )
            return False, old_table_name
    else:
        old_table_name = None
        LOGGER.info(
            f"Entry `{link}` in position `{table_index}` does not exist in imported_tables table."
        )
    try:
        # insert the new table into imported_tables database
        save_csv_to_db(new_table_name, data, schema_name=schema_name)
        LOGGER.info(
            f"Inserted table `{new_table_name}` into {IMPORTED_TABLES_DBNAME} database, schema `{schema_name}`."
        )
        return True, old_table_name
    except Exception as e:
        LOGGER.error(
            f"Error inserting table `{new_table_name}` into {IMPORTED_TABLES_DBNAME} database, schema `{schema_name}`: {e}\n Data: {data}"
        )
        return False, old_table_name


def update_imported_tables(
    api_key: str,
    link: str,
    table_index: int,
    old_table_name: Optional[str],
    table_name: str,
    table_description: str,
) -> bool:
    """
    Updates the imported_tables table in the imported_tables database with the table's info.
    Removes entry from imported_tables table if it already exists.
    """

    if old_table_name:
        try:
            # update imported_tables table
            update_stmt = (
                update(ImportedTables)
                .where(
                    ImportedTables.api_key == api_key,
                    ImportedTables.table_link == link,
                    ImportedTables.table_position == table_index,
                )
                .values(table_name=table_name, table_description=table_description)
            )

            with imported_tables_engine.begin() as imported_tables_connection:
                imported_tables_connection.execute(update_stmt)
                LOGGER.info(f"Updated entry `{table_name}` in imported_tables table.")
            return True
        except Exception as e:
            LOGGER.error(
                f"Error occurred in updating entry `{table_name}` in imported_tables table.: {e}"
            )
            return False
    else:
        try:
            # insert the table's info into imported_tables table
            table_data = {
                "api_key": api_key,
                "table_link": link,
                "table_position": table_index,
                "table_name": table_name,
                "table_description": table_description,
            }
            stmt = insert(ImportedTables).values(table_data)
            with imported_tables_engine.begin() as imported_tables_connection:
                imported_tables_connection.execute(stmt)
                LOGGER.info(
                    f"Inserted entry `{table_name}` into imported_tables table."
                )
            return True
        except Exception as e:
            LOGGER.error(
                f"Error occurred in inserting entry `{table_name}` into imported_tables table: {e}"
            )
            return False


def save_csv_to_db(
    table_name: str,
    data: list[list[str]],
    schema_name: str = None,
) -> bool:
    """
    Saves a csv file to either the internal db or the imported_tables db.
    data is a list of lists where the first list consists of the column names and the rest are the rows.
    """
    df = mk_df(data[1:], data[0])
    try:
        df.to_sql(
            name=table_name,
            con=imported_tables_engine,
            if_exists="replace",
            index=False,
            schema=schema_name,
        )
        return True
    except Exception as e:
        LOGGER.error(e)
        return False
