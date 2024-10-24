import os
from typing import Any, Dict, Optional
from matplotlib import pyplot as plt
import pandas as pd

from generic_utils import format_sql, make_request, normalize_sql
from oracle.celery_app import LOGGER
import seaborn as sns

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")

# explore module constants
TABLE_CSV = "table_csv"
IMAGE = "image"
ARTIFACT_TYPES = [TABLE_CSV, IMAGE]
SUPPORTED_CHART_TYPES = [
    "relplot",
    "catplot",
    "displot",
]


async def gen_sql(api_key: str, db_type: str, question: str, glossary: str) -> str:
    """
    Generate SQL for the given question and glossary, using the Defog API.
    """
    resp = await make_request(
        f"{DEFOG_BASE_URL}/generate_query_chat",
        data={
            "api_key": api_key,
            "dev": False,
            "db_type": db_type,
            "question": question,
            "glossary": glossary,
        },
    )
    # anything that returns a status code other than 200 will return None
    if resp:
        gen_sql = resp["sql"]
        gen_sql = normalize_sql(gen_sql)
        LOGGER.debug(f"Generated SQL: {format_sql(gen_sql)}")
        return gen_sql
    else:
        raise Exception(f"Error in making request to /generate_query_chat")


async def retry_sql_gen(
    api_key: str, question: str, sql: str, error: str, db_type: str
) -> Optional[str]:
    """
    Fix the error that occurred while generating SQL / executing the query.
    Returns the fixed sql query if successful, else None.
    """
    json_data = {
        "api_key": api_key,
        "question": question,
        "previous_query": sql,
        "error": error,
        "db_type": db_type,
    }
    response = await make_request(
        f"{DEFOG_BASE_URL}/retry_query_after_error",
        data=json_data,
    )
    if response:
        new_query = response["new_query"]
        return new_query
    else:
        raise Exception(f"Error in making request to /retry_query_after_error")


async def get_chart_fn(
    api_key: str,
    question: str,
    data: pd.DataFrame,
    dependent_variable: str,
    independent_variable: str,
) -> Optional[Dict]:
    """
    Get the most suitable chart function and arguments for the given data.
    """
    LOGGER.debug(f"Getting sns chart for question: {question}")
    LOGGER.debug(f"dtypes: {data.dtypes}")
    # if we're showing the unique values for only 1 column, hardcode to use a
    # histogram with the number of bins set to the number of unique values.
    if len(data.columns) == 1 and "unique" in question:
        return {
            "name": "displot",
            "parameters": {"kind": "hist", "x": data.columns[0], "bins": len(data)},
        }
    # the statistic names (e.g. count, mean, etc) are in the index after calling
    # `describe` so we need to keep it when exporting to csv
    non_numeric_columns = data.select_dtypes(include="object").columns
    numeric_columns = data.select_dtypes(exclude="object").columns
    LOGGER.debug(f"Numeric columns: {numeric_columns}")
    LOGGER.debug(f"Non-Numeric columns: {non_numeric_columns}")
    if not numeric_columns.empty:
        numeric_columns_summary = (
            data[numeric_columns].describe().to_csv(index=True, float_format="%.2f")
        )
    else:
        numeric_columns_summary = ""
    if not non_numeric_columns.empty:
        qualitative_columns_summary = (
            data[non_numeric_columns].describe(include="object").to_csv(index=True)
        )
    else:
        qualitative_columns_summary = ""
    json_data = {
        "api_key": api_key,
        "question": question,
        "numeric_columns_summary": numeric_columns_summary,
        "qualitative_columns_summary": qualitative_columns_summary,
        "dependent_variable": dependent_variable,
        "independent_variable": independent_variable,
    }
    resp = await make_request(f"{DEFOG_BASE_URL}/get_sns_chart", data=json_data)
    if "name" not in resp or "parameters" not in resp:
        LOGGER.error(f"Error occurred in getting sns chart: {resp}")
        return None
    if resp["name"] not in SUPPORTED_CHART_TYPES:
        LOGGER.error(f"Unsupported chart type: {resp['name']}")
        return None
    return resp


def run_chart_fn(
    chart_fn_params: Dict[str, Any], data: pd.DataFrame, chart_path: str, figsize=(5, 3)
):
    """
    Run the sns plotting function on the data and save the chart to the given path.

    Parameters:
    - chart_fn_params (Dict): Parameters for the chart function, including the
      function name and parameters.
    - data (pd.DataFrame): The data to plot.
    - chart_path (str): The file path to save the chart.
    """
    if not chart_fn_params:
        raise Exception("No chart function provided")
    chart_fn = chart_fn_params["name"]
    kwargs = chart_fn_params.get("parameters", {})
    # replace "" in value with None
    for key, value in kwargs.items():
        if value == "":
            kwargs[key] = None

    plt.figure(figsize=figsize)  # Initialize a new figure

    # Run the sns plotting function on the data
    if chart_fn == "relplot":
        sns.relplot(data, **kwargs)
    elif chart_fn == "displot":
        sns.displot(data, **kwargs)
    elif chart_fn == "catplot":
        sns.catplot(data, **kwargs)

    # rotate x-axis labels if the x column's values has more than 100 characters
    x_col = kwargs.get("x", None)
    if x_col:
        x_col_values = data[x_col]
        # get unique string values of x column and sum the length of all values
        x_col_char_count = sum([len(str(val)) for val in x_col_values.unique()])
        LOGGER.debug(f"X column char count: {x_col_char_count}")
        locs, labels = plt.xticks()
        if x_col_char_count > (figsize[0] * 10):
            LOGGER.debug(f"Rotating x-axis labels")
            plt.setp(labels, rotation=45)

    # Save the figure to the specified path
    plt.savefig(chart_path)
    plt.close()  # Close the figure to free memory


async def gen_data_analysis(
    task_type: str,
    api_key: str,
    generated_qn: str,
    sql: str,
    data_fetched: pd.DataFrame,
    chart_fn_params: Dict[str, Any],
) -> Dict[str, str]:
    """
    Given the user question, generated question and fetched data and chart,
    this will generate a title and summary of the key insights.
    Returns a dictionary with the title and summary.
    """
    # get the data points that are used to generate the chart
    # note that we need to aggregate if the chart implicitly aggregates the data
    chart_fn = chart_fn_params.get("name")
    chart_params = chart_fn_params.get("parameters", {})
    kind = chart_params.get("kind", None)
    y_col = chart_params.get("y", None)
    x_col = chart_params.get("x", None)
    hue_col = chart_params.get("hue", None)
    col_col = chart_params.get("col", None)
    row_col = chart_params.get("row", None)

    grouping_cols = [col for col in [hue_col, col_col, row_col] if col]
    # add x only if it is not numerical and used in relplot
    if x_col and data_fetched[x_col].dtype not in ["int64", "float64"]:
        grouping_cols.append(x_col)
    LOGGER.debug(f"Grouping columns: {grouping_cols}")

    agg_functions = {}
    if y_col:
        if chart_fn == "relplot" and kind == "line":
            agg_functions[y_col] = "mean"
        elif chart_fn == "catplot" and kind == "bar":
            agg_functions[y_col] = "sum"
        elif chart_fn == "catplot" and kind == "count":
            agg_functions[y_col] = "count"
        elif chart_fn == "catplot" and kind in ["box", "violin"]:
            agg_functions[y_col] = [
                lambda x: x.quantile(0.25),
                lambda x: x.median(),
                lambda x: x.quantile(0.75),
            ]
        LOGGER.debug(f"Agg functions: {agg_functions}")

    if not grouping_cols or not agg_functions:
        data_grouped = data_fetched
        aggregated = False
    else:
        if y_col:
            LOGGER.debug(f"data_fetched: {data_fetched.head()}")
            LOGGER.debug(f"columns: {data_fetched.columns}")
            LOGGER.debug(f"dtype: {data_fetched.dtypes}")
            data_grouped = (
                data_fetched.groupby(grouping_cols).agg(agg_functions).reset_index()
            )
        elif chart_fn == "displot":
            data_grouped = data_fetched.groupby(grouping_cols).hist()
        else:
            LOGGER.error(
                f"Edge case not handled for chart_fn: {chart_fn}, chart params: {chart_fn_params}"
            )

        LOGGER.debug(f"Grouped data: {data_grouped}")

        aggregated = len(data_grouped) < len(data_fetched)

    # convert data df to csv
    data_csv = data_grouped.to_csv(float_format="%.3f", header=True, index=False)

    # generate data analysis
    json_data = {
        "task_type": task_type,
        "api_key": api_key,
        "question": generated_qn,
        "sql": sql,
        "data_csv": data_csv,
        "data_aggregated": aggregated,
        "chart_fn": chart_fn,
        "chart_params": chart_params,
    }
    resp = await make_request(
        f"{DEFOG_BASE_URL}/oracle/gen_explorer_data_analysis", data=json_data
    )
    if resp:
        return resp
    else:
        raise Exception(
            f"Error in making request to /oracle/gen_explorer_data_analysis"
        )
