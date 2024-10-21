import os
from typing import Any, Dict, Optional
from matplotlib import pyplot as plt
import pandas as pd
import base64

from celery.utils.log import get_task_logger
from generic_utils import format_sql, make_request, normalize_sql
from utils_logging import LOG_LEVEL
import seaborn as sns

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
LOGGER = get_task_logger(__name__)
LOGGER.setLevel(LOG_LEVEL)

# explore module constants
TABLE_CSV = "table_csv"
IMAGE = "image"
ARTIFACT_TYPES = [TABLE_CSV, IMAGE]
SUPPORTED_CHART_TYPES = [
    "Bar Chart",
    "Table",
    "Line Chart",
    "Boxplot",
    "Heatmap",
    "Scatter Plot",
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
        if x_col_char_count > (figsize[0]*10):
            LOGGER.debug(f"Rotating x-axis labels")
            plt.setp(labels, rotation=45)

    # Save the figure to the specified path
    plt.savefig(chart_path)
    plt.close()  # Close the figure to free memory


async def gen_data_analysis(
    api_key: str,
    user_question: str,
    generated_qn: str,
    sql: str,
    data_df: pd.DataFrame,
    chart_path: str,
    max_rows: int = 50,
) -> Dict[str, str]:
    """
    Given the user question, generated question and fetched data and chart,
    this will generate a title and summary of the key insights.
    Returns a dictionary with the title and summary.
    """
    sampled = False
    if len(data_df) > max_rows:
        LOGGER.debug(
            f"Sampling data down from {len(data_df)} to {max_rows} for analysis"
        )
        data_df = data_df.sample(max_rows)
        sampled = True

    # convert data df to csv
    data_csv = data_df.to_csv(float_format="%.3f", header=True, index=False)

    # convert chart to base64
    if chart_path:
        with open(chart_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    else:
        base64_image = None

    # generate data analysis
    json_data = {
        "api_key": api_key,
        "user_question": user_question,
        "generated_qn": generated_qn,
        "sql": sql,
        "data_csv": data_csv,
        "chart": base64_image,
        "sampled": sampled,
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
