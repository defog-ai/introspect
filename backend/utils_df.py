# helper functions for dataframes
from typing import List, Tuple
import pandas as pd

from utils_logging import LOGGER

TYPE_DATE = "date"
TYPE_TIME = "time"
TYPE_DATETIME = "datetime"
TYPE_STRING = "string"
TYPE_INTEGER = "int64"
TYPE_FLOAT = "float64"
TYPE_MONEY = "money"

REGEX_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
REGEX_TIME_PATTERN = r"^\d{2}:\d{2}:\d{2}$"
REGEX_DATETIME_PATTERN = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
REGEX_INTEGER_PATTERN = r"^\d+$"
REGEX_FLOAT_PATTERN = r"^\d+(\.\d+)?$"
REGEX_MONEY_PATTERN = r"^\$?\d{1,3}(,?\d{3})*(\.\d{2})?$"


def determine_column_type(column: pd.Series) -> str:
    """
    Determines the type of the column based on the data.
    We get the "lowest common denominator" type of the column. i.e. if the column
    has a mix of dates and normal text, we return 'string'.
    """
    if column.dtype == "object":
        # Check if it's a date, time, or datetime column
        date_matches = column.astype(str).str.match(REGEX_DATE_PATTERN)
        if date_matches.all():
            return TYPE_DATE
        time_matches = column.astype(str).str.match(REGEX_TIME_PATTERN)
        if time_matches.all():
            return TYPE_TIME
        datetime_matches = column.astype(str).str.match(REGEX_DATETIME_PATTERN)
        if datetime_matches.all():
            return TYPE_DATETIME
        # Check if it's an integer column
        integer_matches = column.astype(str).str.match(REGEX_INTEGER_PATTERN)
        if integer_matches.all():
            return TYPE_INTEGER
        # Check if it's a float column
        float_matches = column.astype(str).str.match(REGEX_FLOAT_PATTERN)
        if float_matches.all():
            return TYPE_FLOAT
        # Check if it's a money column
        money_matches = column.astype(str).str.match(REGEX_MONEY_PATTERN)
        if money_matches.all():
            return TYPE_MONEY
        return TYPE_STRING
    elif column.dtype == "int64":
        return TYPE_INTEGER
    elif column.dtype == "float64":
        return TYPE_FLOAT
    elif column.dtype == "datetime64[ns]":
        return TYPE_DATETIME
    else:
        return TYPE_STRING


def mk_df(data: List, columns: List[str]) -> pd.DataFrame:
    """
    Make a dataframe from a list of lists, with the appropriate column data types.
    """
    df = pd.DataFrame(data, columns=columns)

    for col in df.columns:
        column_non_null = df[col].dropna()
        format_type = determine_column_type(column_non_null)

        if format_type == TYPE_DATETIME:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif format_type == TYPE_DATE:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif format_type == TYPE_TIME:
            # note that the .dt.time accessor coerces the type to 'object'
            df[col] = pd.to_datetime(
                df[col], format="%H:%M:%S", errors="coerce"
            ).dt.time
        elif format_type == TYPE_INTEGER:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("int64")
        elif format_type == TYPE_FLOAT:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
        elif format_type == TYPE_MONEY:
            # Convert money strings to float by removing currency symbols and commas
            df[col] = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    return df


def get_columns_summary(df: pd.DataFrame) -> Tuple[str, str, str]:
    """
    Get the summary of the numeric and non-numeric columns.
    """
    numeric_columns = df.columns[df.dtypes.apply(lambda x: pd.api.types.is_numeric_dtype(x))]
    date_columns = df.columns[df.dtypes.apply(lambda x: pd.api.types.is_datetime64_any_dtype(x))]
    non_numeric_columns = pd.Index(set(df.columns) - set(numeric_columns) - set(date_columns))
    LOGGER.debug(f"numeric_columns: {numeric_columns}")
    LOGGER.debug(f"non_numeric_columns: {non_numeric_columns}")
    LOGGER.debug(f"date_columns: {date_columns}")
    # the statistic names (e.g. count, mean, etc) are in the index after calling
    # `describe` so we need to keep it when exporting to csv
    if not non_numeric_columns.empty:
        non_numeric_columns_summary = df[non_numeric_columns].describe(include="object").to_csv(index=True)
    else:
        non_numeric_columns_summary = ""
    if not numeric_columns.empty:
        numeric_columns_summary = df[numeric_columns].describe().to_csv(index=True, float_format="%.2f")
    else:
        numeric_columns_summary = ""
    if not date_columns.empty:
        date_columns_summary = ""
        for col in date_columns:
            date_columns_summary += f"Column name: {col}\n"
            date_columns_summary += f"Value counts:\n{df[col].value_counts().to_csv(index=True)}\n"
    else:
        date_columns_summary = ""
    return numeric_columns_summary, non_numeric_columns_summary, date_columns_summary
