"""
Legacy function aliases for backward compatibility.
These functions are wrappers around the class methods in the utility modules.
"""

from .name_utils import NameUtils
from .datetime_utils import DateTimeUtils
from .type_utils import TypeUtils
from .db_utils import DbUtils


def clean_table_name(table_name: str, existing=None):
    """Legacy wrapper for NameUtils.clean_table_name"""
    return NameUtils.clean_table_name(table_name, existing or [])


def sanitize_column_name(col_name: str):
    """Legacy wrapper for NameUtils.sanitize_column_name"""
    return NameUtils.sanitize_column_name(col_name)


def is_date_column_name(col_name):
    """Legacy wrapper for DateTimeUtils.is_date_column_name"""
    return DateTimeUtils.is_date_column_name(col_name)


def is_time_column_name(col_name):
    """Legacy wrapper for DateTimeUtils.is_time_column_name"""
    return DateTimeUtils.is_time_column_name(col_name)


def can_parse_date(val):
    """Legacy wrapper for DateTimeUtils.can_parse_date"""
    return DateTimeUtils.can_parse_date(val)


def can_parse_time(val):
    """Legacy wrapper for DateTimeUtils.can_parse_time"""
    return DateTimeUtils.can_parse_time(val)


def to_float_if_possible(val):
    """Legacy wrapper for TypeUtils.to_float_if_possible"""
    return TypeUtils.to_float_if_possible(val)


def guess_column_type(series, column_name=None, sample_size=50):
    """Legacy wrapper for TypeUtils.guess_column_type"""
    return TypeUtils.guess_column_type(series, column_name, sample_size)


def convert_values_to_postgres_type(value, target_type: str):
    """Legacy wrapper for TypeUtils.convert_values_to_postgres_type"""
    return TypeUtils.convert_values_to_postgres_type(value, target_type)


def create_table_sql(table_name: str, columns: dict[str, str]):
    """Legacy wrapper for DbUtils.create_table_sql"""
    return DbUtils.create_table_sql(table_name, columns)


async def export_df_to_postgres(
    df, table_name: str, db_connection_string: str, chunksize: int = 5000
):
    """Legacy wrapper for DbUtils.export_df_to_postgres"""
    return await DbUtils.export_df_to_postgres(
        df, table_name, db_connection_string, chunksize
    )