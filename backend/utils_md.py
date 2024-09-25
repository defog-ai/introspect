########################################
### Metadata Related Functions Below ###
########################################

import re
from typing import Dict, List
import sqlglot


def convert_data_type_postgres(dtype: str) -> str:
    """
    Convert the data type to be used in SQL queries to be postgres compatible
    """
    # remove any question marks from dtype and convert to lowercase
    dtype = re.sub(r"[\/\?]", "", dtype.lower())
    if dtype in {"int", "tinyint", "integer", "int64"}:
        return "integer"
    elif dtype in {"double", "float64"}:
        return "double precision"
    elif dtype in {"varchar", "user-defined", "enum", "longtext", "string"}:
        return "text"
    elif dtype.startswith("number"):
        return "numeric"
    # if regex match dtype starting with datetime or timestamp, return timestamp
    elif dtype.startswith("datetime") or dtype.startswith("timestamp"):
        return "timestamp"
    elif dtype == "array":
        return "text[]"
    elif "byte" in dtype:
        return "text"
    elif dtype == "object":
        return "text"
    else:
        return dtype


def mk_create_table_ddl(table_name: str, columns: List[Dict[str, str]]) -> str:
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
        dtype = convert_data_type_postgres(column["data_type"])
        if i < len(columns) - 1:
            md_create += f"  {col_name} {dtype},\n"
        else:
            # avoid the trailing comma for the last line
            md_create += f"  {col_name} {dtype}\n"
    md_create += ");\n"
    return md_create


def mk_create_ddl(md: Dict[str, List[Dict[str, str]]]) -> str:
    """
    Return a DDL statement for creating tables from a metadata dictionary
    {'table1': [
        {'column_name': 'col1', 'data_type': 'int'},
        {'column_name': 'col2', 'data_type': 'text'},
        {'column_name': 'col3', 'data_type': 'text'},
    ],
    'table2': [
    ...
    ]}
    """
    md_create = ""
    available_schemas = set()
    for table, contents in md.items():
        if "." in table:
            schema_name = table.split(".")[-2]
            table_name = table.split(".")[-1]
            if schema_name not in available_schemas:
                md_create += f"CREATE SCHEMA IF NOT EXISTS {schema_name};\n"
                available_schemas.add(schema_name)
        table_dict = contents
        md_create += mk_create_table_ddl(table_name, table_dict)
    return md_create


def metadata_error(
    table_metadata: Dict[str, List[Dict[str, str]]], db_type: str
) -> str:
    """
    Check if the metadata is valid for the given database type, and returns the associated error if it not. If sqlglot can parse the DDL, we return None. Else, we return the error message.
    """
    # first, make sure that all *combinations* of table names and column names are unique
    table_column_names = set()
    for table_name, columns in table_metadata.items():
        for col in columns:
            if table_name + "." + col["column_name"] in table_column_names:
                return f"Duplicate values exist for column name {col['column_name']} in table {table_name}. In addition, there might be other similar duplication issues. Please correct the metadata and re-upload."
            else:
                table_column_names.add(table_name + "." + col["column_name"])

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
