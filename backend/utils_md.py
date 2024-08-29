########################################
### Metadata Related Functions Below ###
########################################

import re
from typing import Dict, List


def convert_data_type_postgres(dtype: str) -> str:
    """
    Convert the data type to be used in SQL queries to be postgres compatible
    """
    # remove any question marks from dtype and convert to lowercase
    dtype = re.sub(r"[\/\?]", "", dtype.lower())
    if dtype in {"int", "tinyint", "integer"}:
        return "integer"
    elif dtype == "double":
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
    else:
        return dtype

def mk_create_table_ddl(table_name: str, columns: List[Dict[str, str]]) -> str:
    """
    Return a DDL statement for creating a table from a list of columns
    `columns` is a list of dictionaries with the following keys:
    - column_name: str
    - data_type: str
    - column_description: str
    """
    md_create = ""
    md_create += f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    for i, column in enumerate(columns):
        col_name = column["column_name"]
        # if column name has spaces and hasn't been wrapped in double quotes, wrap it in double quotes
        if " " in col_name and not col_name.startswith('"'):
            col_name = f'"{col_name}"'
        dtype = convert_data_type_postgres(column["data_type"])
        col_desc = column.get("column_description", "").replace("\n", " ")
        if col_desc:
            col_desc = f" --{col_desc}"
        if i < len(columns) - 1:
            md_create += f"  {col_name} {dtype},{col_desc}\n"
        else:
            # avoid the trailing comma for the last line
            md_create += f"  {col_name} {dtype}{col_desc}\n"
    md_create += ");\n"
    return md_create


def mk_create_ddl(md: Dict[str, List[Dict[str, str]]]) -> str:
    """
    Return a DDL statement for creating tables from a metadata dictionary
    `md` can have either a dictionary of schemas or a dictionary of tables.
    The former (with schemas) would look like this:
    {'schema1':
        {'table1': [
            {'column_name': 'col1', 'data_type': 'int', 'column_description': 'primary key'},
            {'column_name': 'col2', 'data_type': 'text', 'column_description': 'not null'},
            {'column_name': 'col3', 'data_type': 'text', 'column_description': ''},
        ],
        'table2': [
        ...
        ]},
    'schema2': ...}
    Schema is optional, and if not provided, the dictionary will be treated as
    a single schema of the form:
    {'table1': [
        {'column_name': 'col1', 'data_type': 'int', 'column_description': 'primary key'},
        {'column_name': 'col2', 'data_type': 'text', 'column_description': 'not null'},
        {'column_name': 'col3', 'data_type': 'text', 'column_description': ''},
    ],
    'table2': [
    ...
    ]}
    """
    md_create = ""
    for schema_or_table, contents in md.items():
        is_schema = isinstance(contents, dict)
        if is_schema:
            schema = schema_or_table
            tables = contents
            schema_ddl = f"CREATE SCHEMA IF NOT EXISTS {schema};\n"
            md_create += schema_ddl
            for table_name, table_dict in tables.items():
                schema_table_name = f"{schema}.{table_name}"
                md_create += mk_create_table_ddl(schema_table_name, table_dict)
        else:
            table_name = schema_or_table
            table_dict = contents
            md_create += mk_create_table_ddl(table_name, table_dict)
    return md_create