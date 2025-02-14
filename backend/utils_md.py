########################################
### Metadata Related Functions Below ###
########################################

import sqlglot
from sqlalchemy import delete, insert, select, update
from db_models import DefogMetadata
from db_config import engine


async def get_metadata(api_key: str) -> list[dict[str, str]]:
    """
    Get metadata for a given API key.
    Returns a list of dictionaries, each containing:
        - table_name: str
        - column_name: str
        - data_type: str
        - column_description: str
    """
    async with engine.begin() as conn:
        metadata_result = await conn.execute(
            select(
                DefogMetadata.table_name,
                DefogMetadata.column_name,
                DefogMetadata.data_type,
                DefogMetadata.column_description,
            )
            .where(DefogMetadata.api_key == api_key)
            .order_by(DefogMetadata.table_name, DefogMetadata.column_name)
        )
        # Convert to list of dictionaries with proper keys
        metadata = [
            {
                "table_name": row[0],
                "column_name": row[1],
                "data_type": row[2],
                "column_description": row[3] or "",  # Convert None to empty string
            }
            for row in metadata_result.fetchall()
        ]
    return metadata


async def set_metadata(api_key: str, table_metadata: list[dict[str, str]]):
    """
    Update or insert metadata for a given API key.
    Args:
        api_key: The API key to update metadata for
        table_metadata: List of dictionaries containing column metadata with keys:
            - table_name: str
            - column_name: str
            - data_type: str
            - column_description: str (optional)
    """
    if not table_metadata:
        return

    # Validate required fields exist in each item
    required_fields = {"table_name", "column_name", "data_type"}
    for item in table_metadata:
        missing_fields = required_fields - set(item.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

    async with engine.begin() as conn:
        # Delete existing metadata for this api_key
        await conn.execute(
            delete(DefogMetadata).where(DefogMetadata.api_key == api_key)
        )
        # Insert the new metadata
        await conn.execute(
            insert(DefogMetadata),
            [
                {
                    "api_key": api_key,
                    "table_name": item["table_name"],
                    "column_name": item["column_name"],
                    "data_type": item["data_type"],
                    "column_description": item.get(
                        "column_description", ""
                    ),  # Default to empty string if not provided
                }
                for item in table_metadata
            ],
        )


def mk_create_table_ddl(table_name: str, columns: list[dict[str, str]]) -> str:
    """
    Return a DDL statement for creating a table from a list of columns
    `columns` is a list of dictionaries with the following keys:
    - column_name: str
    - data_type: str
    """
    md_create = ""
    md_create += f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    for i, column in enumerate(columns):
        col_name = column["column_name"]
        # if column name has spaces and hasn't been wrapped in double quotes, wrap it in double quotes
        if " " in col_name and not col_name.startswith('"'):
            col_name = f'"{col_name}"'
        dtype = column["data_type"]
        if i < len(columns) - 1:
            md_create += f"  {col_name} {dtype},\n"
        else:
            # avoid the trailing comma for the last line
            md_create += f"  {col_name} {dtype}\n"
    md_create += ");\n"
    return md_create


def mk_create_ddl(md: list[dict[str, str]]) -> str:
    """
    Return a DDL statement for creating tables from a metadata list
    [
        {'table_name': 'table1', 'column_name': 'col1', 'data_type': 'int'},
        {'table_name': 'table1', 'column_name': 'col2', 'data_type': 'text'},
        {'table_name': 'table2', 'column_name': 'col1', 'data_type': 'text', 'column_description': 'description'},
    ]
    """
    md_create = ""
    available_schemas = set("")
    md_dict = {}
    for column in md:
        if "." in column["table_name"]:
            table_name_split = column["table_name"].split(".", 1)
            if len(table_name_split) == 2:
                schema_name = table_name_split[0]
                table_name = table_name_split[1]
            else:
                schema_name = ""
                table_name = table_name_split[0]
            if schema_name not in available_schemas:
                md_create += f"CREATE SCHEMA IF NOT EXISTS {schema_name};\n"
                available_schemas.add(schema_name)
        else:
            table_name = column["table_name"]
        if table_name not in md_dict:
            md_dict[table_name] = []
        md_dict[table_name].append(column)
    for table_name, columns in md_dict.items():
        md_create += mk_create_table_ddl(table_name, columns)
    return md_create


def check_metadata_validity(
    table_metadata: list[dict[str, str]], db_type: str
) -> str | None:
    """
    Check if the metadata is valid for the given database type, and returns the associated error if it not. If sqlglot can parse the DDL, we return None. Else, we return the error message.
    """
    # first, make sure that all *combinations* of table names and column names are unique
    table_column_names = set()
    for item in table_metadata:
        if (item["table_name"], item["column_name"]) in table_column_names:
            return f"Duplicate values exist for column name {item['column_name']} in table {item['table_name']}. In addition, there might be other similar duplication issues. Please correct the metadata and re-upload."
        else:
            table_column_names.add((item["table_name"], item["column_name"]))
    # next, check if the DDL is valid for the given database type
    ddl = mk_create_ddl(table_metadata)
    if db_type == "sqlserver":
        syntax = "tsql"
    else:
        syntax = db_type
    try:
        sqlglot.parse(ddl, read=syntax)
        return None
    except Exception as e:
        return str(e)
