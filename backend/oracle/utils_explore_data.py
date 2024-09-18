import os
from typing import Dict, List, Optional
import pandas as pd
import base64

from celery.utils.log import get_task_logger
from utils_logging import LOG_LEVEL
from defog.query import execute_query
from generic_utils import is_sorry, make_request, normalize_sql
from agents.planner_executor.tools.plotting import (
    bar_plot,
    line_plot,
    boxplot,
    heatmap,
    scatter_plot,
)


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
    if resp.get("ran_successfully", False) == True:
        gen_sql = resp["sql"]
        gen_sql = normalize_sql(gen_sql)
        LOGGER.info(f"Generated SQL: {gen_sql}")
        return gen_sql
    else:
        LOGGER.error(
            f"Error occurred in generating SQL for question: {resp}\nQuestion: {question}"
        )
        return None


async def execute_sql(
    api_key: str,
    db_type: str,
    db_creds: Dict,
    question: str,
    sql: str,
) -> Optional[pd.DataFrame]:
    """
    Run the SQL query on the database and return the results as a dataframe using the execute_query method in the Defog Python library
    TODO refactor to use SQLAlchemy instead of defog.query.execute_query
    """
    if sql:
        if is_sorry(sql):
            LOGGER.error(
                f"Couldn't answer with a valid SQL query for question {question}"
            )
            return None
        try:
            colnames, data, _ = execute_query(
                query=sql,
                api_key=api_key,
                db_type=db_type,
                db_creds=db_creds,
                question=question,
                retries=0,
            )
            df = pd.DataFrame(data, columns=colnames)
            return df
        except Exception as e:
            LOGGER.error(f"Error occurred in running SQL: {e}\nSQL: {sql}")
            return None
    LOGGER.error("No SQL generated to execute")
    return None


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
    try:
        response = await make_request(
            f"{DEFOG_BASE_URL}/retry_query_after_error",
            data=json_data,
        )
        new_query = response["new_query"]
        return new_query
    except Exception as e:
        LOGGER.error(f"Error occurred in retrying SQL generation: {str(e)}")
        return None


async def get_chart_type(api_key: str, columns: list, question: str) -> Dict[str, str]:
    """
    Get the appropriate chart type for the given dataframe and question.
    Only viz types 'Table', 'Bar Chart', 'Line Chart', 'Boxplot', 'Heatmap', 'Scatter Plot' are supported now.
    Prompt in DEFOG_BASE_URL/get_chart_type must be modified for additional chart types.
    Returns a dictionary with the chart type and the x and y axis columns.
    TODO: Refactor this and downstream defog-backend-python to return appropriate
    sns functions and parameters for plotting
    """
    json_data = {
        "api_key": api_key,
        "question": question,
        "columns": columns,
        "chart_types": SUPPORTED_CHART_TYPES,
    }
    resp = await make_request(
        f"{DEFOG_BASE_URL}/get_chart_type",
        data=json_data,
    )
    if "chart_type" in resp:
        return resp
    return {"chart_type": "Table", "xAxisColumns": [], "yAxisColumns": []}


async def plot_chart(
    report_chart_dir: str,
    df: pd.DataFrame,
    chart_type: str,
    x_column: List[str],
    y_column: List[str],
) -> Optional[str]:
    """
    Plot the chart for the given dataframe and chart type using execute_tool in agents/planner_executor/execute_tool.py
    Only line plots, boxplots, and heat maps are supported now.
    Returns the path to the chart image. Unsupported chart types or tables will return None.
    """
    # get the appropriate tool name and folder name for the chart type
    if "bar" in chart_type.lower():
        plotting_fn = bar_plot
        folder_name = "barplots"
    elif "line" in chart_type.lower():
        plotting_fn = line_plot
        folder_name = "linecharts"
    elif "box" in chart_type.lower():
        plotting_fn = boxplot
        folder_name = "boxplots"
    elif "heat" in chart_type.lower():
        plotting_fn = heatmap
        folder_name = "heatmaps"
    elif "scatter" in chart_type.lower():
        plotting_fn = scatter_plot
        folder_name = "scatterplots"
    else:
        LOGGER.info(f"Unsupported chart type: {chart_type}")
        return None
    # create the directory if it doesn't exist
    if not os.path.exists(f"{report_chart_dir}/{folder_name}"):
        os.makedirs(f"{report_chart_dir}/{folder_name}", exist_ok=True)
        LOGGER.info(f"Created directory {report_chart_dir}/{folder_name}")

    global_dict = {
        "analysis_assets_dir": report_chart_dir,
    }

    # execute the tool
    if isinstance(x_column, list) and len(x_column) > 0:
        x_column = x_column[0]
    if isinstance(y_column, list) and len(y_column) > 0:
        y_column = y_column[0]
    try:
        resp = await plotting_fn(
            full_data=df, x_column=x_column, y_column=y_column, global_dict=global_dict
        )
        # includes folder_name e.g. linecharts/xxxx.png
        chart_filename = resp["outputs"][0]["chart_images"][0]["path"]
    except Exception as e:

        LOGGER.error(f"Error occurred in plotting chart: {str(e)}")
        LOGGER.debug(f"Plotting function: {plotting_fn}")
        LOGGER.debug(
            f"df: {df}\nchart_type: {chart_type}\nx_column: {x_column}\ny_column: {y_column}"
        )
        LOGGER.debug(
            f"Global dict: {global_dict}\nCurrent dir: {os.getcwd()}\nReport dir: {report_chart_dir}"
        )
        import traceback

        LOGGER.debug(traceback.format_exc())
        return None
    full_chart_path = f"{report_chart_dir}/{chart_filename}"
    return full_chart_path


async def gen_data_analysis(
    api_key: str,
    user_question: str,
    generated_qn: str,
    sql: str,
    data_df: pd.DataFrame,
    chart_path: str,
) -> Dict[str, str]:
    """
    Given the user question, generated question and fetched data and chart,
    this will generate a title and summary of the key insights.
    Returns a dictionary with the title and summary.
    """
    sampled = False
    if len(data_df) > 50 and not chart_path:
        data_df = data_df.sample(50)
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
    if "error" in resp:
        LOGGER.error(f"Error occurred in generating data analysis: {resp['error']}")
        return {
            "table_description": None,
            "image_description": None,
            "title": None,
            "summary": None,
        }
    return resp
