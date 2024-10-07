import collections
import re
from typing import Dict

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
from sqlalchemy import text
from utils_logging import LOGGER
from sqlalchemy.ext.asyncio import create_async_engine
from generic_utils import is_sorry

# Functions mostly lifted from https://github.com/defog-ai/sql-eval/blob/main/eval/eval.py
# but adapted to use the engine from db_utils and without some extra labels like
# query_category


async def execute_sql(
    db_type: str,
    db_creds: Dict,
    question: str,
    sql: str,
) -> pd.DataFrame | None:
    """
    Asynchronously run the SQL query on the user's database using SQLAlchemy and return the results as a dataframe.
    """
    if not sql:
        LOGGER.error(f"No SQL generated to execute for question {question}")
        return None

    if is_sorry(sql):
        LOGGER.error(f"Obtained Sorry SQL query for question {question}")
        return None

    if db_type == "postgres":
        connection_uri = f"postgresql+asyncpg://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
        async_engine = create_async_engine(connection_uri)
    elif db_type == "sqlite":
        connection_uri = f"sqlite+aiosqlite:///{db_creds['database']}"
        async_engine = create_async_engine(connection_uri)
    elif db_type == "mysql":
        connection_uri = f"mysql+aiomysql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
        async_engine = create_async_engine(connection_uri)
    elif db_type == "sqlserver":
        connection_uri = f"mssql+aioodbc://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
        async_engine = create_async_engine(connection_uri)
    else:
        LOGGER.error(
            f"Unsupported db_type for executing query: {db_type}. Must be one of 'postgres', 'sqlite', 'mysql', 'sqlserver'"
        )
        return None
    LOGGER.debug(f"db_type: {db_type}, connection_uri: {connection_uri}")
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text(sql))
            data = result.all()
            colnames = list(result.keys())
            LOGGER.info(
                f"Query successfully executed. Col names: {colnames}, Data: {data}\nSQL: {sql}"
            )
    except Exception as e:
        LOGGER.error(f"Error occurred in running SQL: {e}\nSQL: {sql}")
        return None
    finally:
        await async_engine.dispose()

    df = pd.DataFrame(data, columns=colnames)
    return df


def deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = df.columns.tolist()
    if len(cols) != len(set(cols)):
        duplicates = [
            item for item, count in collections.Counter(cols).items() if count > 1
        ]
        for dup in duplicates:
            indices = [i for i, x in enumerate(cols) if x == dup]
            for i in indices:
                cols[i] = f"{dup}_{i}"
        df.columns = cols
    return df


def normalize_table(df: pd.DataFrame, question: str, sql: str = None) -> pd.DataFrame:
    """
    Normalizes a dataframe by:
    1. removing all duplicate rows
    2. sorting columns in alphabetical order
    3. sorting rows using values from first column to last (if question does not ask for ordering)
    4. resetting index
    """
    # remove duplicate rows, if any
    df = df.drop_duplicates()

    # sort columns in alphabetical order of column names
    sorted_df = df.reindex(sorted(df.columns), axis=1)

    # check if query_category is 'order_by' and if question asks for ordering
    has_order_by = False
    pattern = re.compile(r"\b(order|sort|arrange)\b", re.IGNORECASE)
    in_question = re.search(pattern, question.lower())  # true if contains
    if in_question:
        has_order_by = True

        if sql:
            # determine which columns are in the ORDER BY clause of the sql generated, using regex
            pattern = re.compile(r"ORDER BY[\s\S]*", re.IGNORECASE)
            order_by_clause = re.search(pattern, sql)
            if order_by_clause:
                order_by_clause = order_by_clause.group(0)
                # get all columns in the ORDER BY clause, by looking at the text between ORDER BY and the next semicolon, comma, or parantheses
                pattern = re.compile(r"(?<=ORDER BY)(.*?)(?=;|,|\)|$)", re.IGNORECASE)
                order_by_columns = re.findall(pattern, order_by_clause)
                order_by_columns = (
                    order_by_columns[0].split() if order_by_columns else []
                )
                order_by_columns = [
                    col.strip().rsplit(".", 1)[-1] for col in order_by_columns
                ]

                ascending = False
                # if there is a DESC or ASC in the ORDER BY clause, set the ascending to that
                if "DESC" in [i.upper() for i in order_by_columns]:
                    ascending = False
                elif "ASC" in [i.upper() for i in order_by_columns]:
                    ascending = True

                # remove whitespace, commas, and parantheses
                order_by_columns = [col.strip() for col in order_by_columns]
                order_by_columns = [
                    col.replace(",", "").replace("(", "") for col in order_by_columns
                ]
                order_by_columns = [
                    i
                    for i in order_by_columns
                    if i.lower()
                    not in ["desc", "asc", "nulls", "last", "first", "limit"]
                ]

                # get all columns in sorted_df that are not in order_by_columns
                other_columns = [
                    i for i in sorted_df.columns.tolist() if i not in order_by_columns
                ]

                # only choose order_by_columns that are in sorted_df
                order_by_columns = [
                    i for i in order_by_columns if i in sorted_df.columns.tolist()
                ]
                sorted_df = sorted_df.sort_values(
                    by=order_by_columns + other_columns, ascending=ascending
                )

                sorted_df = sorted_df[other_columns + order_by_columns]

    if not has_order_by:
        # sort rows using values from first column to last
        sorted_df = sorted_df.sort_values(by=list(sorted_df.columns))

    # reset index
    sorted_df = deduplicate_columns(sorted_df)
    sorted_df = sorted_df.reset_index(drop=True)
    return sorted_df


def compare_df(
    df_gold: pd.DataFrame,
    df_gen: pd.DataFrame,
    question: str,
    query_gold: str = None,
    query_gen: str = None,
) -> bool:
    """
    Compares two dataframes and returns True if they are the same, else False.
    query_gold and query_gen are the original queries that generated the respective dataframes.
    """
    # drop duplicates to ensure equivalence
    try:
        is_equal = df_gold.values == df_gen.values
        if is_equal.all():
            return True
    except:
        try:
            is_equal = df_gold.values == df_gen.values
            if is_equal:
                return True
        except:
            pass

    df_gold = normalize_table(df_gold, question, query_gold)
    df_gen = normalize_table(df_gen, question, query_gen)

    # perform same checks again for normalized tables
    if df_gold.shape != df_gen.shape:
        return False
    # fill NaNs with -99999 to handle NaNs in the dataframes for comparison
    df_gen.fillna(-99999, inplace=True)
    df_gold.fillna(-99999, inplace=True)
    is_equal = df_gold.values == df_gen.values
    try:
        return is_equal.all()
    except:
        return is_equal


def subset_df(
    df_sub: pd.DataFrame,
    df_super: pd.DataFrame,
    question: str,
    query_super: str = None,
    query_sub: str = None,
    verbose: bool = False,
) -> bool:
    """
    Checks if df_sub is a subset of df_super.
    """
    if df_sub.empty:
        return False  # handle cases for empty dataframes

    # make a copy of df_super so we don't modify the original while keeping track of matches
    df_super_temp = df_super.copy(deep=True)
    matched_columns = []
    df_sub = deduplicate_columns(df_sub)
    df_super_temp = deduplicate_columns(df_super_temp)
    for col_sub_name in df_sub.columns:
        col_match = False
        for col_super_name in df_super_temp.columns:
            col_sub = df_sub[col_sub_name].sort_values().reset_index(drop=True)
            col_super = (
                df_super_temp[col_super_name].sort_values().reset_index(drop=True)
            )

            try:
                assert_series_equal(
                    col_sub, col_super, check_dtype=False, check_names=False
                )
                col_match = True
                matched_columns.append(col_super_name)
                # remove col_super_name to prevent us from matching it again
                df_super_temp = df_super_temp.drop(columns=[col_super_name])
                break
            except AssertionError:
                continue

        if not col_match:
            if verbose:
                print(f"no match for {col_sub_name}")
            return False

    df_sub_normalized = normalize_table(df_sub, question, query_sub)

    # get matched columns from df_super, and rename them with columns from df_sub, then normalize
    df_super_matched = df_super[matched_columns].rename(
        columns=dict(zip(matched_columns, df_sub.columns))
    )
    df_super_matched = normalize_table(df_super_matched, question, query_super)

    try:
        assert_frame_equal(df_sub_normalized, df_super_matched, check_dtype=False)
        return True
    except AssertionError:
        return False


async def compare_query_results(
    query_gold: str,
    query_gen: str,
    df_gen: pd.DataFrame,
    question: str,
    db_type: str,
    db_creds: Dict[str, str],
) -> Dict[str, bool]:
    """
    Compares the results of two queries and returns a dictionary with the keys:
    'correct' and 'subset' indicating if the queries are correct and if the result of the
    generated query is a subset of the golden query.
    """
    correct = False
    try:
        df_gold = await execute_sql(db_type, db_creds, question, query_gold)
        # check if df_gold is an empty dataframe
        # this is because the function errors out when df_gold is empty
        if df_gold.empty and df_gen.empty:
            correct = False
        elif compare_df(df_gold, df_gen, question, query_gold, query_gen):
            correct = True
        elif subset_df(df_gold, df_gen, question, query_gen, query_gold):
            correct = True
    except Exception as e:
        import traceback

        LOGGER.error(f"Error in compare_query_results: {e}")
        LOGGER.error(traceback.format_exc())
    finally:
        if "dfg" in locals():
            del dfg
        return {"correct": correct}
