"""
Utilities for data processing, type inference, and database operations.
This package provides helpers for cleaning, processing, and loading data into PostgreSQL.
"""

# Import classes
from .name_utils import NameUtils
from .datetime_utils import DateTimeUtils
from .type_utils import TypeUtils
from .excel_utils import ExcelUtils
from .csv_utils import CSVUtils
from .db_utils import DbUtils

# Import constants
from .constants import POSTGRES_RESERVED_WORDS

# Import legacy functions for backward compatibility
from .legacy import (
    clean_table_name,
    sanitize_column_name,
    is_date_column_name,
    is_time_column_name,
    can_parse_date,
    can_parse_time,
    to_float_if_possible,
    guess_column_type,
    convert_values_to_postgres_type,
    create_table_sql,
    export_df_to_db,
    export_df_to_postgres,
)

from sqlalchemy.ext.asyncio import create_async_engine

__all__ = [
    # Classes
    "NameUtils",
    "DateTimeUtils",
    "TypeUtils",
    "ExcelUtils",
    "CSVUtils",
    "DbUtils",
    
    # Constants
    "POSTGRES_RESERVED_WORDS",
    
    # Legacy functions
    "clean_table_name",
    "sanitize_column_name",
    "is_date_column_name",
    "is_time_column_name",
    "can_parse_date",
    "can_parse_time",
    "to_float_if_possible",
    "guess_column_type",
    "convert_values_to_postgres_type",
    "create_table_sql",
    "export_df_to_db",
    "export_df_to_postgres",

    # sqlalchemy
    "create_async_engine",
]