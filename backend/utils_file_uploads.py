import re
from uuid import uuid4
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dateutil import parser

from utils_logging import LOGGER

POSTGRES_RESERVED_WORDS = {
    "select",
    "from",
    "where",
    "join",
    "table",
    "order",
    "group",
    "by",
    "create",
    "drop",
    "insert",
    "update",
    "delete",
    "alter",
    "column",
    "user",
    "and",
    "or",
    "not",
    "null",
    "true",
    "false",
    "primary",
    "key",
    "foreign",
    "unique",
    "check",
    "default",
    "index",
    "on",
    "as",
    "asc",
    "desc",
    "varchar",
    "int",
    "bigint",
    "float",
    "decimal",
    "text",
    "boolean",
    "date",
    "timestamp",
}


def clean_table_name(table_name: str):
    """
    Cleans a table name by snake casing it and making it lower case.
    If the table name is not a string, raises a ValueError.
    If the table name is empty, adds a random string.
    If the table name has special characters, quotes it.
    """
    if not isinstance(table_name, str):
        raise ValueError("Table name must be a string.")
        
    validated = str(table_name).strip().lower()
    validated = re.sub(r"[^a-zA-Z0-9_]", "_", validated)

    if not validated:
        validated = f"table_{uuid4().hex[:7]}"

    return validated


def is_date_column_name(col_name):
    """
    Check if a column name indicates it might contain date/time data.
    Returns True if the column name contains date-related terms.
    """
    if not isinstance(col_name, str):
        return False
        
    # Normalize the column name for better matching
    name_lower = col_name.lower()
    
    # List of date-related terms to check for
    date_terms = [
        'date', 'time', 'year', 'month', 'day', 'quarter', 'qtr',
        'yr', 'mm', 'dd', 'yyyy', 'created', 'modified', 'updated',
        'timestamp', 'dob', 'birth', 'start', 'end', 'period',
        'calendar', 'fiscal', 'dtm', 'dt', 'ymd', 'mdy', 'dmy'
    ]
    
    # Check if any date term appears in the column name
    for term in date_terms:
        if term in name_lower:
            return True
            
    # Check for common date patterns (e.g., date_of_birth, create_dt)
    if re.search(r'(_|^)(dt|date|time)(_|$)', name_lower):
        return True
        
    return False


def can_parse_date(val):
    """
    Return True if `val` looks like a date.

    For non-string inputs, we convert to string. If the string is
    purely numeric, we allow four digits (a year), six digits (YYMMDD),
    or eight digits (a compact date like YYYYMMDD). Otherwise, we require 
    the presence of a typical date separator.
    """
    if not isinstance(val, str):
        val = str(val)

    # Trim whitespace
    val = val.strip()

    # If the string is empty, it's not a date.
    if not val:
        return False

    # Common date patterns
    common_date_patterns = [
        # MM/DD/YYYY or DD/MM/YYYY
        r'^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}$',
        # YYYY/MM/DD
        r'^\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}$',
        # Month name formats: Jan 01, 2020 or January 1, 2020
        r'^[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{2,4}$',
        # 01-Jan-2020 or 1-January-20
        r'^\d{1,2}[/\-\.\s]+[A-Za-z]{3,9}\.?[/\-\.\s]+\d{2,4}$',
        # Formats like 01Jan2023 or 01JAN2023
        r'^\d{1,2}[A-Za-z]{3,9}\d{2,4}$'
    ]
    
    # Check against common date patterns first for efficiency
    for pattern in common_date_patterns:
        if re.match(pattern, val):
            try:
                parser.parse(val)
                return True
            except:
                # If it matches pattern but fails parsing, continue checking
                pass
    
    # If the string is all digits, only allow specific lengths
    if re.fullmatch(r"\d+", val):
        if len(val) in (4, 6, 8):  # Added 6 for YYMMDD format
            try:
                parser.parse(val)
                return True
            except Exception:
                return False
        else:
            return False

    # For strings that are not all digits, require at least one common date separator.
    if not re.search(r"[\s/\-\.:]", val):
        # One more attempt with dateutil parser for formats like "01Jan2023"
        try:
            parsed_date = parser.parse(val, fuzzy=False)
            year = parsed_date.year
            if 1900 <= year <= 2100:
                return True
            return False
        except:
            return False

    # Finally, try to parse it with dateutil.
    try:
        parsed_date = parser.parse(val, fuzzy=True)
        # Additional validation: check if the parsed date is reasonable
        # (between 1900 and 2100)
        year = parsed_date.year
        if 1900 <= year <= 2100:
            return True
        return False
    except Exception:
        return False


def to_float_if_possible(val):
    """
    Helper function: attempt to parse to numeric after cleaning
    e.g. remove $, commas, random whitespace
    """
    if not val:
        return None
        
    try:
        # Handle accounting negative numbers (123.45) -> -123.45
        # Convert accounting-style negatives to regular negatives
        val_str = str(val).strip()
        if val_str.startswith("(") and val_str.endswith(")"):
            val_str = "-" + val_str[1:-1].strip("$").strip()
        
        # First, clean the value by removing non-numeric symbols except . - + e E
        cleaned_val = re.sub(r"[^\d.\-+eE]", "", val_str)
    
        # Check if the cleaned value is empty or just a symbol
        if cleaned_val in ("", ".", "-", "+"):
            return None
    
        # Check if the string has a reasonable proportion of numeric characters
        # Count digits in the original value
        digit_count = sum(c.isdigit() for c in val_str)
        # Count total alphanumeric characters in the original value
        alphanum_count = sum(c.isalnum() for c in val_str)
    
        if digit_count == 0 or alphanum_count == 0:
            return None
    
        # If the string alphanumcount > digitcount, it's TEXT
        # Example: NDA1, NDA2, 2007AMAN01, etc
        if alphanum_count > digit_count:
            return None
    
        # Try to handle scientific notation correctly
        return float(cleaned_val)
    except:
        return None


def guess_column_type(series, column_name=None, sample_size=50):
    """
    Guess the most appropriate Postgres column type for a given Pandas Series of strings.
    We sample up to `sample_size` non-null elements to make the guess.
    Also considers the column name for date detection.
    """
    # Drop nulls/empty
    non_null_values = [str(v) for v in series.dropna() if str(v).strip() != ""]

    # If there's nothing in this column, assume TEXT
    if len(non_null_values) == 0:
        return "TEXT"

    # Sample some values (to limit computational overhead if large)
    sampled_values = non_null_values[:sample_size]

    # Check if column name suggests a date
    column_suggests_date = column_name is not None and is_date_column_name(column_name)
    
    # Check for percentage values in column
    pct_count = sum(1 for v in sampled_values if str(v).strip().endswith("%"))
    pct_ratio = pct_count / len(sampled_values)
    
    # If many percentage values, use DOUBLE PRECISION or TEXT
    if pct_ratio > 0.3:
        return "DOUBLE PRECISION" if pct_ratio > 0.8 else "TEXT"
    
    # Determine fraction that are valid dates
    date_count = sum(can_parse_date(v) for v in sampled_values)
    date_ratio = date_count / len(sampled_values)

    # Determine fraction that are valid numeric
    float_parsed = [to_float_if_possible(v) for v in sampled_values]
    numeric_count = sum(x is not None for x in float_parsed)
    numeric_ratio = numeric_count / len(sampled_values)

    # Decide on type
    # Priority: 
    # 1. If column name suggests date and some values can be parsed as dates -> TIMESTAMP
    # 2. If enough are numeric -> check int vs float
    # 3. Else if enough are date -> TIMESTAMP
    # 4. Else TEXT

    # 1) Date column name check with partial date values
    if column_suggests_date and date_ratio > 0.4:  # Lower threshold for columns with date-suggesting names
        return "TIMESTAMP"

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
            # If the column name suggests a date and values can be integers (like year numbers)
            if column_suggests_date:
                return "TIMESTAMP"
            # Otherwise use BIGINT
            return "BIGINT"
        else:
            # Use DOUBLE PRECISION
            return "DOUBLE PRECISION"

    # 3) Check date
    # If a majority (>70% - lowered threshold) is parseable as date, pick a date/timestamp
    if date_ratio > 0.7:
        return "TIMESTAMP"

    # 4) Default
    return "TEXT"


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
    if not isinstance(col_name, str):
        col_name = str(col_name)
    
    col_name = col_name.strip().lower()

    # replace any `%` characters with `perc`
    col_name = col_name.replace("%", "perc")

    # replace any `&` characters with `and`
    col_name = col_name.replace("&", "and")

    # Replace any character not in [a-z0-9_] with underscore
    col_name = re.sub(r"[^a-z0-9_]", "_", col_name)

    # Collapse multiple underscores into single
    col_name = re.sub(r"_+", "_", col_name)

    # Strip leading/trailing underscores
    col_name = col_name.strip("_")

    # If empty after stripping, fallback
    if not col_name:
        col_name = "col"

    # If it starts with digit, prepend underscore
    if re.match(r"^\d", col_name):
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
    if value is None or pd.isna(value):
        return None
        
    val_str = str(value).strip()
    
    # Handle common NULL-like string values
    if val_str.lower() in ("", "null", "none", "nan", "   "):
        return None

    if target_type == "TIMESTAMP":
        # Attempt date parsing
        try:
            # Check for invalid date patterns before trying to parse
            if re.search(r'(\d{4}-\d{2}-\d{2})-[a-zA-Z]', val_str):  # Like "2023-01-01-extra"
                return None
                
            # Set fuzzy=False to be stricter with parsing
            parsed_date = parser.parse(val_str, fuzzy=False)
            
            # Additional validation: check if the parsed date is reasonable
            # (between 1900 and 2100)
            year = parsed_date.year
            if 1900 <= year <= 2100:
                return parsed_date
            return None
        except:
            # One more attempt with fuzzy=True but only for values with date-like patterns
            try:
                if re.search(r'\d{1,4}[-/. ]\d{1,2}[-/. ]\d{1,4}', val_str) or \
                   re.search(r'[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{2,4}', val_str) or \
                   re.search(r'\d{1,2}[/\-\.\s]+[A-Za-z]{3,9}\.?[/\-\.\s]+\d{2,4}', val_str):
                    parsed_date = parser.parse(val_str, fuzzy=True)
                    year = parsed_date.year
                    if 1900 <= year <= 2100:
                        return parsed_date
                return None
            except:
                return None

    elif target_type in ("BIGINT", "DOUBLE PRECISION"):
        # Skip processing for values that are clearly not numeric
        if re.search(r'^[a-zA-Z]', val_str):  # Starts with letter
            return None
            
        # Handle accounting negative numbers (123.45) -> -123.45
        if val_str.startswith("(") and val_str.endswith(")"):
            val_str = "-" + val_str[1:-1].strip("$").strip()
            
        # Check for percentage values
        if val_str.endswith("%"):
            if target_type == "BIGINT":
                return None  # Don't try to convert percentages to integers
            # For DOUBLE PRECISION, strip the % and divide by 100
            val_str = val_str.rstrip("%").strip()
            try:
                return float(re.sub(r"[^\d.\-+eE]", "", val_str)) / 100
            except:
                return None
            
        # Special handling for BIGINT with currency or currency codes
        if target_type == "BIGINT":
            # Handle currency symbol at beginning
            if val_str.startswith('$'):
                val_str = val_str[1:].strip()
            # Handle currency code at end like "USD"
            elif re.search(r'\s+[A-Z]{3}$', val_str):
                val_str = re.sub(r'\s+[A-Z]{3}$', '', val_str)
                
        # Remove non-numeric chars except '.', '-', '+', 'e', 'E'
        cleaned_val = re.sub(r"[^\d.\-+eE]", "", val_str)
        if cleaned_val in ("", ".", "-", "+"):
            return None
            
        # Check for obviously invalid numeric patterns
        if cleaned_val.count('.') > 1 or cleaned_val.count('-') > 1 or cleaned_val.count('+') > 1:
            return None
            
        # Check for obviously invalid comma patterns for numbers (like 1,2,3)
        if re.search(r'\d,\d,\d', val_str):
            return None
            
        # Check for specific patterns we want to reject
        if re.search(r'[0-9a-fA-F]+', val_str) and val_str.startswith("0x"):  # Hex notation
            return None
            
        # Check for values containing slashes or multiple symbols that indicate mathematical expressions
        if "/" in val_str or "+" in val_str[1:]:
            return None
            
        # For BIGINT, after all the special handling, reject if we still have letters
        if target_type == "BIGINT" and re.search(r'[a-zA-Z]', val_str):
            return None
            
        try:
            if target_type == "BIGINT":
                float_val = float(cleaned_val)
                # Check if the float is NaN or infinity before converting to int
                if pd.isna(float_val) or float_val in (float("inf"), float("-inf")):
                    return None
                # Validate the range is within -2^63 to 2^63-1 (PostgreSQL BIGINT range)
                if float_val < -9223372036854775808 or float_val > 9223372036854775807:
                    return None
                return int(float_val)  # or directly int(...) if you want strict
            else:  # DOUBLE PRECISION
                return float(cleaned_val)
        except:
            return None

    else:
        # TEXT or fallback
        # Return the original string value without stripping whitespace
        return str(value)


async def export_df_to_postgres(
    df: pd.DataFrame, table_name: str, db_connection_string: str, chunksize: int = 5000
):
    """
    1. Reads CSV into a pandas DataFrame (as strings).
    2. Infers column types for Postgres, intelligently detecting date columns.
    3. Creates table in Postgres.
    4. Inserts data chunk by chunk.
    """
    # Make a copy of the dataframe to avoid modifying the original
    df = df.copy()
    
    # Handle NaN values before proceeding
    df = df.fillna(value="")
    
    # Store original column names for type inference
    original_cols = list(df.columns)
    
    # Insert data chunk-by-chunk to handle large CSVs
    col_list = list(df.columns)
    safe_col_list = [sanitize_column_name(c) for c in col_list]  # safe col names
    
    # Create a column name mapping for reference
    col_name_mapping = dict(zip(safe_col_list, original_cols))
    
    # Update dataframe with sanitized column names
    df.columns = safe_col_list

    # Create a SQLAlchemy engine
    engine = create_async_engine(db_connection_string)

    # Infer data types using original column names for better date detection
    inferred_types = {}
    for col in df.columns:
        # Pass the original column name for better date detection
        original_name = col_name_mapping.get(col, col)
        inferred_types[col] = guess_column_type(df[col], column_name=original_name)

    LOGGER.info(inferred_types)

    # Convert inferred types to Postgres types
    converted_df = df.copy()
    for col in df.columns:
        converted_df[col] = df[col].apply(
            lambda value: convert_values_to_postgres_type(
                value, target_type=inferred_types[col]
            )
        )

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
        # Replace any remaining NaN values with None for database compatibility
        for idx, row in enumerate(converted_df.replace({np.nan: None}).to_dict("records")):
            rows_to_insert.append(row)

            # If we reached the chunk size or the end, do a batch insert
            if len(rows_to_insert) == chunksize or idx == len(converted_df) - 1:
                await conn.execute(text(insert_sql), rows_to_insert)
                rows_to_insert = []

    print(f"Successfully imported {len(df)} rows into table '{table_name}'.")
    return {"success": True, "inferred_types": inferred_types}