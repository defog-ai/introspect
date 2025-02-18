import re
from uuid import uuid4
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dateutil import parser

POSTGRES_RESERVED_WORDS = {
    'select', 'from', 'where', 'join', 'table',
    'order', 'group', 'by', 'create', 'drop', 'insert',
    'update', 'delete', 'alter', 'column', 'user', 'and',
    'or', 'not', 'null', 'true', 'false', 'primary',
    'key', 'foreign', 'unique', 'check', 'default',
    'index', 'on', 'as', 'asc', 'desc', 'varchar', 'int',
    'bigint', 'float', 'decimal', 'text', 'boolean', 'date', 'timestamp',
}


def clean_table_name(table_name: str):
    """
    Cleans a table name by snake casing it and making it lower case.
    If the table name is not a string, raises a ValueError.
    If the table name is empty, adds a random string.
    If the table name has special characters, quotes it.
    """
    validated = str(table_name).strip().lower()
    validated = re.sub(r"[^a-zA-Z0-9_]", "_", validated)

    if not isinstance(table_name, str):
        raise ValueError("Table name must be a string.")
    if not validated:
        validated = f"table_{uuid4().hex[:7]}"

    return validated


def can_parse_date(val):
    """
    Helper function: check if something can be a date
    """
    try:
        parser.parse(val, fuzzy=True)
        return True
    except:
        return False


def to_float_if_possible(val):
    """
    Helper function: attempt to parse to numeric after cleaning
    e.g. remove $, commas, random whitespace
    """
    cleaned_val = re.sub(r'[^\d.\-+eE]', '', val)  # remove any non-numeric symbol except . - + e E
    if cleaned_val in ('', '.', '-', '+'):
        return None
    try:
        return float(cleaned_val)
    except:
        return None


def guess_column_type(series, sample_size=50):
    """
    Guess the most appropriate Postgres column type for a given Pandas Series of strings.
    We sample up to `sample_size` non-null elements to make the guess.
    """
    # Drop nulls/empty
    non_null_values = [v for v in series.dropna() if v.strip() != '']

    # If there's nothing in this column, assume TEXT
    if len(non_null_values) == 0:
        return 'TEXT'

    # Sample some values (to limit computational overhead if large)
    sampled_values = non_null_values[:sample_size]

    # Determine fraction that are valid dates
    date_count = sum(can_parse_date(v) for v in sampled_values)
    date_ratio = date_count / len(sampled_values)

    # Determine fraction that are valid numeric
    float_parsed = [to_float_if_possible(v) for v in sampled_values]
    numeric_count = sum(x is not None for x in float_parsed)
    numeric_ratio = numeric_count / len(sampled_values)

    # Decide on type
    # Priority: If enough are date -> DATE or TIMESTAMP
    #           Else if enough are numeric, check int vs float
    #           Else TEXT
    # We can tweak the thresholds to handle partial columns better

    # 1) Check date
    # If a large majority (>80% for instance) is parseable as date, pick a date/timestamp
    if date_ratio > 0.8:
        # We can further refine if we want DATE vs. TIMESTAMP. We'll assume TIMESTAMP for broad coverage.
        return 'TIMESTAMP'

    # 2) Check numeric
    # If a large majority (>80%) is parseable as numeric, figure out if integer or decimal
    if numeric_ratio > 0.8:
        # Check if everything is "integer-like" (no decimal part) among the valid portion
        are_ints = []
        for val in float_parsed:
            if val is not None:
                # Check if val is integral
                are_ints.append(val.is_integer())
        if all(are_ints):
            # Use BIGINT or INT based on range
            # For simplicity, let's just use BIGINT.
            return 'BIGINT'
        else:
            # Use DOUBLE PRECISION or NUMERIC
            # We'll choose DOUBLE PRECISION for simplicity
            return 'DOUBLE PRECISION'

    # 3) Default
    return 'TEXT'


def sanitize_column_name(col_name: str):
    """
    Convert a column name into a "safe" Postgres identifier:
      1) Lowercase everything.
      2) Replace invalid characters with underscores.
      3) Collapse multiple underscores into one.
      4) Remove leading/trailing underscores.
      5) If it starts with a digit, prepend an underscore.
      6) If empty, fallback to "col" + some random suffix or index.
      7) Optionally rename if it's a Postgres reserved keyword.
    """
    col_name = col_name.strip().lower()

    # Replace any character not in [a-z0-9_] with underscore
    col_name = re.sub(r'[^a-z0-9_]', '_', col_name)

    # Collapse multiple underscores into single
    col_name = re.sub(r'_+', '_', col_name)

    # Strip leading/trailing underscores
    col_name = col_name.strip('_')

    # If empty after stripping, fallback
    if not col_name:
        col_name = "col"

    # If it starts with digit, prepend underscore
    if re.match(r'^\d', col_name):
        col_name = f"_{col_name}"

    # If it's a reserved keyword, add suffix
    if col_name in POSTGRES_RESERVED_WORDS:
        col_name = f"{col_name}_col"

    return col_name


def create_table_sql(table_name: str, columns: dict[str, str]):
    """
    Build a CREATE TABLE statement given a table name and a dict of column_name -> data_type.
    """
    cols = []
    for col_name, col_type in columns.items():
        # Make sure column name is safe
        safe_col_name = sanitize_column_name(col_name)
        # Compose "col_name col_type"
        cols.append(f'"{safe_col_name}" {col_type}')
    cols_str = ", ".join(cols)
    sql = f'CREATE TABLE "{table_name}" ({cols_str});'
    return sql


def convert_values_to_postgres_type(value: str, target_type: str):
    """
    Convert a string `value` to the appropriate Python object for insertion into Postgres
    based on `target_type`. If conversion fails, return None (NULL).
    """
    if value is None or str(value).strip() == '':
        return None
    
    val_str = str(value).strip()

    if target_type == 'TIMESTAMP':
        # Attempt parse
        try:
            return parser.parse(val_str, fuzzy=True)
        except:
            return None
    
    elif target_type in ('BIGINT', 'DOUBLE PRECISION'):
        # Remove non-numeric chars except '.', '-', '+', 'e', 'E'
        cleaned_val = re.sub(r'[^\d.\-+eE]', '', val_str)
        if cleaned_val in ('', '.', '-', '+'):
            return None
        try:
            if target_type == 'BIGINT':
                return int(float(cleaned_val))  # or directly int(...) if you want strict
            else:  # DOUBLE PRECISION
                return float(cleaned_val)
        except:
            return None
    
    else:
        # TEXT or fallback
        return val_str


async def import_csv_to_postgres(df: pd.DataFrame, table_name: str, db_connection_string: str, chunksize: int=5000):
    """
    1. Reads CSV into a pandas DataFrame (as strings).
    2. Infers column types for Postgres.
    3. Creates table in Postgres.
    4. Inserts data chunk by chunk.
    """
    # Insert data chunk-by-chunk to handle large CSVs
    col_list = list(df.columns)
    safe_col_list = [sanitize_column_name(c) for c in col_list]  # safe col names
    df.columns = safe_col_list

    # Create a SQLAlchemy engine
    engine = create_async_engine(db_connection_string)
    
    # Infer data types
    inferred_types = {}
    for col in df.columns:
        inferred_types[col] = guess_column_type(df[col])
    
    # convert inferred types to Postgres types
    for col in df.columns:
        df[col] = df[col].apply(lambda value: convert_values_to_postgres_type(value, target_type=inferred_types[col]))

    # Create table in Postgres
    create_stmt = create_table_sql(table_name, inferred_types)
    async with engine.begin() as conn:
        # Drop table if it already exists (optional)
        await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}";'))
        await conn.execute(text(create_stmt))
    
    insert_cols = ", ".join(f'"{c}"' for c in safe_col_list)
    
    # this `:colname` placeholder is asyncpg specific
    # psycopg2 uses %s, non-postgres things have different placeholders
    # TODO: make this more modular
    placeholders = ", ".join([f":{c}" for c in safe_col_list])
    insert_sql = f'INSERT INTO "{table_name}" ({insert_cols}) VALUES ({placeholders})'

    # psycopg2 / sqlalchemy "raw" execution
    async with engine.begin() as conn:
        # We'll insert in batches
        rows_to_insert = []
        for idx, row in enumerate(df.to_dict("records")):
            rows_to_insert.append(row)

            # If we reached the chunk size or the end, do a batch insert
            if len(rows_to_insert) == chunksize or idx == len(df) - 1:
                await conn.execute(text(insert_sql), rows_to_insert)
                rows_to_insert = []
    
    print(f"Successfully imported {len(df)} rows into table '{table_name}'.")
    return {
        "success": True,
        "inferred_types": inferred_types
    }