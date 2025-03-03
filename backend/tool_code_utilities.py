# includes utilties that a user can import when writing their tool code
# top level for a cleaner import statement
# from tool_code_utilities import xx

from defog.query import async_execute_query_once
import re
import pandas as pd
from db_utils import get_db_type_creds
from utils_sql import safe_sql, retry_query_after_error
from typing import Tuple


async def fetch_query_into_df(
    db_name: str,
    sql_query: str,
    question: str = None,
) -> Tuple[pd.DataFrame, str]:
    """
    Runs a sql query and stores the results in a pandas dataframe.
    """
    db_type, db_creds = await get_db_type_creds(db_name)

    # make sure not unsafe
    if not safe_sql(sql_query):
        raise ValueError("Unsafe SQL Query")

    try:
        colnames, data = await async_execute_query_once(
            query=sql_query,
            db_type=db_type,
            db_creds=db_creds,
        )
    except Exception as e:
        # retry exactly once
        error_msg = str(e)
        sql_query = (
            await retry_query_after_error(
                question=question,
                sql=sql_query,
                error=error_msg,
                db_name=db_name,
            )
        )["sql"]

        colnames, data = await async_execute_query_once(
            query=sql_query,
            db_type=db_type,
            db_creds=db_creds,
        )

    df = pd.DataFrame(data, columns=colnames)

    # if this df has any columns that have lists, remove those columns
    for col in df.columns:
        if df[col].apply(type).eq(list).any():
            df = df.drop(col, axis=1)

    df.sql_query = sql_query
    return df, sql_query


def natural_sort_function(l, ascending=True):
    """
    Sorts a list or a pandas series in a natural way.
    If it's a list of numbers or datetimes, just sort them normally.
    If it's a string, check if there are numbers in the string, and sort them as a heirarchy of numbers.
    Example 1: ['a', 'b', 'c'] would be sorted as ['a', 'b', 'c']
    Example 2: ['1', '10', '2'] would be sorted as ['1', '2', '10']
    Example 3: ['a1', 'a10', 'a2'] would be sorted as ['a1', 'a2', 'a10']
    Example 4: ['C1D1', 'C10D10', 'C2D2', 'C1D11'] would be sorted as ['C1D1', 'C1D11', 'C2D2', 'C10D10']
    """

    def convert(text):
        return int(text) if text.isdigit() else text

    def alphanum_key(key):
        return [convert(c) for c in re.split("([0-9]+)", key)]

    if type(l) == pd.Series:
        # TODO do this in a more efficient way
        l = l.tolist()

    l.sort(key=alphanum_key, reverse=not ascending)
    return l


def natural_sort(df, time_column, units=None, ascending=True):
    """
    Sorts a dataframe in a natural way, using the natural_sort_function.
    """
    if df[time_column].dtype == "object":
        try:
            order = natural_sort_function(df[time_column].unique().tolist())
            df[time_column] = pd.Categorical(
                df[time_column], categories=order, ordered=True
            )
        except Exception as e:
            # if there are any errors, just pass
            pass
        if units:
            df = df.sort_values(by=[units, time_column], ascending=ascending)
        else:
            df = df.sort_values(by=time_column, ascending=ascending)
    else:
        df = df.sort_values(by=time_column, ascending=ascending)
    return df
