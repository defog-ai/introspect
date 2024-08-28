# includes utilties that a user can import when writing their tool code
# top level for a cleaner import statement
# from tool_code_utilities import xx

import asyncio
import yaml
from defog import Defog
from defog.query import execute_query
import re
import json
import pandas as pd
import os
from db_utils import get_db_type_creds

analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)


import matplotlib.pyplot as plt
import seaborn as sns

available_colors = plt.colormaps()

sns.set_palette(["#009D94", "#FF5C1C", "#0057CF", "#691A6B", "#FFBD00"])


# make sure the query does not contain any malicious commands like drop, delete, etc.
def safe_sql(query):
    if query is None:
        return False

    query = query.strip()
    query = query.replace("\n", " ").replace("\t", " ")
    query = " " + query.lower() + " "
    if (
        " drop " in query
        or " delete " in query
        or " truncate " in query
        or " append " in query
        or " insert " in query
        or " update " in query
    ):
        return False

    return True


async def fetch_query_into_df(
    api_key: str, sql_query: str, temp: bool = False
) -> pd.DataFrame:
    """
    Runs a sql query and stores the results in a pandas dataframe.
    """

    # important note: this is currently a blocking call
    # TODO: add an option to the defog library to make this async
    if not temp:
        res = get_db_type_creds(api_key)
        db_type, db_creds = res
    else:
        db_type = "postgres"
        db_creds = {
            "host": "agents-postgres",
            "port": 5432,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres",
        }

    # make sure not unsafe
    if not safe_sql(sql_query):
        raise ValueError("Unsafe SQL Query")

    colnames, data, new_sql_query = await asyncio.to_thread(
        execute_query, sql_query, api_key, db_type, db_creds, retries=2, temp=temp
    )

    if len(data) == 0:
        data = [["no data found" for _ in colnames]]

    # again, make sure new query that was run is safe
    # make sure not unsafe
    if not safe_sql(new_sql_query):
        raise ValueError("Unsafe SQL Query")

    df = pd.DataFrame(data, columns=colnames)

    # if this df has any columns that have lists, remove those columns
    for col in df.columns:
        if df[col].apply(type).eq(list).any():
            df = df.drop(col, axis=1)

    if new_sql_query:
        sql_query = new_sql_query
    else:
        sql_query = sql_query

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


default_top_level_imports = "\n\n".join(
    [
        "from agents.planner_executor.tool_helpers.tool_param_types import (",
        "  DBColumn,",
        "  DropdownSingleSelect,",
        "  ListWithDefault,",
        "  db_column_list_type_creator,",
        ")",
        "from tool_code_utilities import available_colors",
        "import pandas",
        "import pandas as pd",
    ]
)


def add_default_imports(code):
    """
    Adds the default imports to the code.
    """
    return default_top_level_imports + "\n\n" + code


def fix_savefig_calls(code):
    """
    Fixes the savefig calls in the code by changing the path and always appending analysis_assets_dir variable to the path.
    """
    # check both for double and single quote
    code = code.replace('savefig("', f'savefig({analysis_assets_dir} + "')
    code = code.replace("savefig('", f"savefig({analysis_assets_dir} + '")
    # remove jic we got two slashes
    code = code.replace("//", "/")
    return code
