# helper functions for dataframes
from typing import List
import pandas as pd

TYPE_DATE = "date"
TYPE_TIME = "time"
TYPE_DATETIME = "datetime"
TYPE_STRING = "string"
TYPE_INTEGER = "int64"
TYPE_FLOAT = "float64"

REGEX_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
REGEX_TIME_PATTERN = r"^\d{2}:\d{2}:\d{2}$"
REGEX_DATETIME_PATTERN = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
REGEX_INTEGER_PATTERN = r"^\d+$"
REGEX_FLOAT_PATTERN = r"^\d+(\.\d+)?$"


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

    return df
