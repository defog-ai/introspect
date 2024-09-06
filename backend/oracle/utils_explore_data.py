import os
from typing import Dict, Optional
import pandas as pd
import base64

from celery.utils.log import get_task_logger
from utils_logging import LOG_LEVEL
from defog import Defog
from defog.query import execute_query
from generic_utils import is_sorry, make_request, normalize_sql
from agents.planner_executor.execute_tool import execute_tool


DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
LOGGER = get_task_logger(__name__)
LOGGER.setLevel(LOG_LEVEL)


async def gen_sql(api_key: str, db_type: str, question: str, glossary: str) -> str:
    """
    Generate SQL for the given question and glossary, using the Defog API.
    """
    resp = await make_request(
        f"{DEFOG_BASE_URL}/generate_query_chat",
        json={
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
) -> Optional[Dict]:
    """
    Run the SQL query on the database and return the results as a dataframe using the execute_query method in the Defog Python library
    """
    if sql:
        if is_sorry(sql):
            LOGGER.error(f"Couldn't answer with a valid SQL query for question {question}")
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


async def get_chart_type(api_key: str, columns: list, question: str) -> str:
    """
    Get the appropriate chart type for the given dataframe and question.
    Only viz types 'Table', 'Bar Chart', 'Line Chart', 'Pie Chart', 'Boxplot', 'Heatmap', 'Scatter Plot' are supported now.
    Prompt in DEFOG_BASE_URL/get_chart_type must be modified for additional chart types.
    Returns a dictionary with the chart type and the x and y axis columns.
    """
    json_data = {
        "api_key": api_key,
        "question": question,
        "columns": columns,
    }
    resp = await make_request(
        f"{DEFOG_BASE_URL}/get_chart_type",
        json=json_data,
    )
    if "chart_type" in resp:
        return resp
    return {"chart_type": "Table", "xAxisColumns": [], "yAxisColumns": []}


async def plot_chart(
    api_key: str,
    report_id: int,
    df: pd.DataFrame,
    chart_type: str,
    x_column: list,
    y_column: list,
) -> str:
    """
    Plot the chart for the given dataframe and chart type using execute_tool in agents/planner_executor/execute_tool.py
    Only line plots, boxplots, and heat maps are supported now.
    Returns the path to the chart image. Unsupported chart types or tables will return None.
    """
    # get the appropriate tool name and folder name for the chart type
    if "line" in chart_type.lower():
        tool_name = "line_plot"
        folder_name = "linecharts"
    elif "box" in chart_type.lower():
        tool_name = "boxplot"
        folder_name = "boxplots"
    elif "heat" in chart_type.lower():
        tool_name = "heatmap"
        folder_name = "heatmaps"
    else:
        tool_name = "table"
    if tool_name == "table":
        return None
    else:
        tool_function_inputs = {
            "full_data": df,
            "x_column": x_column[0],
            "y_column": y_column[0],
        }

    # create the directory to save the chart
    current_dir = os.getcwd()
    report_chart_dir = os.path.join(
        current_dir, f"oracle/reports/{api_key}/report_{report_id}"
    )
    if not os.path.exists(f"{report_chart_dir}/{folder_name}"):
        os.makedirs(f"{report_chart_dir}/{folder_name}", exist_ok=True)
        LOGGER.info(f"Created directory {report_chart_dir}/{folder_name}")
    global_dict = {
        "analysis_assets_dir": report_chart_dir,
    }

    # execute the tool
    resp = await execute_tool(tool_name, tool_function_inputs, global_dict=global_dict)
    if "error_message" in resp[0]:
        LOGGER.error(f"Error occurred in plotting chart: {resp[0]['error_message']}")
        return None
    chart_filename = resp[0]["outputs"][0]["chart_images"][0][
        "path"
    ]  # includes folder_name e.g. linecharts/xxxx.png
    full_chart_path = f"{report_chart_dir}/{chart_filename}"
    return full_chart_path


async def gen_data_analysis(
    api_key: str,
    user_question: str,
    generated_qn: str,
    data_df: pd.DataFrame,
    chart_path: str,
) -> str:
    """
    Given the user question, generated question and fetched data and chart,
    this will generate a title and summary of the key insights.
    Returns a dictionary with the title and summary.
    """
    if len(data_df) > 50 and not chart_path:
        LOGGER.error(
            f"Data too large to generate analysis for question: {generated_qn}"
        )
        return {"table_description": None, "image_description": None, "title": None, "summary": None}

    # convert data df to csv
    data_csv = data_df.to_csv(float_format="%.3f", header=True)

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
        "data_csv": data_csv,
        "chart": base64_image,
    }
    resp = await make_request(
        f"{DEFOG_BASE_URL}/oracle/gen_explorer_data_analysis", json=json_data
    )
    if "error" in resp:
        LOGGER.error(f"Error occurred in generating data analysis: {resp['error']}")
        return {"table_description": None, "image_description": None, "title": None, "summary": None}
    return resp
