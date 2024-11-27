import asyncio
import os
import time
import traceback
from typing import Any, Dict

import pandas as pd
from db_utils import get_db_type_creds
from generic_utils import make_request
from oracle.celery_app import LOGGER
from oracle.constants import TaskType
from oracle.utils_explore_data import (
    ANOMALIES_CSV,
    CORRELATION,
    FETCHED_TABLE_CSV,
    IMAGE,
    TABLE_CSV,
    gen_data_analysis,
    gen_sql,
    get_anomalies,
    get_chart_df,
    get_chart_fn,
    get_correlation,
    retry_sql_gen,
    run_chart_fn,
)
from utils_logging import save_timing
from utils_sql import execute_sql

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
MAX_ANALYSES = 5
MAX_ROUNDS = 1
RETRY_DATA_FETCH = 1
RETRY_CHART_GEN = 1


async def explore_data(
    api_key: str,
    report_id: str,
    task_type: TaskType,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will explore the data, by generating a series of exploratory
    data analysis (EDA) plots and tables, which are relevant to the data provided.
    Side Effects:
    - Intermediate data and plots will be saved in the report_id's directory.

    Outputs a list of data analyses, each containing the following keys:
    - analysis_id: int
    - generated_qn: str
    - artifacts: Dict[str, Dict[str, str]]
        - (outer key) artifact_type: str, one of table_csv, image
            - (inner key) artifact_content: str, e.g. csv content, image path
            - (inner value) artifact_description: str, e.g. table of prices,
                scatter plot of x vs y
    - working: Dict[str, str]
        - generated_sql: str
        - reason_for_qn: str
        - reason_for_analysis: str
    - title: str, title of the data analysis
    - summary: str, summary of the data analysis
    - evaluation: Dict[str, float, bool, bool]
        - qn_relevance: float
        - analysis_usefulness: bool
        - analysis_newness: bool
    """
    user_question = inputs["user_question"]
    gather_context = outputs["gather_context"]
    context = gather_context.get("context", "")
    problem_statement = gather_context.get("problem_statement", "")
    db_type, db_creds = get_db_type_creds(api_key)
    max_rounds = inputs.get("max_rounds", MAX_ROUNDS)

    # create the directory to save the chart
    current_dir = os.getcwd()
    report_chart_dir = os.path.join(
        current_dir, f"oracle/reports/{api_key}/report_{report_id}"
    )
    os.makedirs(report_chart_dir, exist_ok=True)

    # generate initial explorer questions
    json_data = {
        "api_key": api_key,
        "user_question": user_question,
        "n_gen_qns": inputs.get("max_analyses", MAX_ANALYSES),
        "task_type": task_type.value,
        "gather_context": gather_context,
    }
    LOGGER.info(f"Generating explorer questions")
    generated_qns_response = await make_request(
        DEFOG_BASE_URL + "/oracle/gen_explorer_qns", json_data
    )
    if "error" in generated_qns_response and generated_qns_response["error"]:
        LOGGER.error(
            f"Error occurred in generating explorer questions: {generated_qns_response['error']}"
        )
        return None

    generated_qns = generated_qns_response["generated_questions"]  # list of dict
    dependent_variable = generated_qns_response["dependent_variable"]  # dict
    independent_variable_groups = generated_qns_response[
        "independent_variable_groups"
    ]  # dict

    LOGGER.debug(f"Generated questions with data: {len(generated_qns)}")

    analyses = []
    round = 0
    summary_all = ""
    while True:
        tasks = []
        for i, question_dict in enumerate(generated_qns):
            # question used by 1st round question generation
            generated_qn = question_dict["question"]
            independent_variable_group_name = question_dict["group_name"]
            independent_variable_group = independent_variable_groups[
                independent_variable_group_name
            ]
            independent_variable_group["name"] = independent_variable_group_name
            if not independent_variable_group:
                LOGGER.error(
                    f"Independent variable group not found for {i}: {generated_qn}"
                )
                continue
            tasks.append(
                explore_generated_question(
                    api_key,
                    user_question,
                    task_type,
                    i,
                    generated_qn,
                    dependent_variable,
                    independent_variable_group,
                    context,
                    db_type,
                    db_creds,
                    report_chart_dir,
                    inputs.get("retry_data_fetch", RETRY_DATA_FETCH),
                )
            )
        answers = await asyncio.gather(*tasks)
        # remove None answers and add to analyses
        non_empty_answers = []
        for ans in answers:
            if ans:
                ans["round"] = round
                non_empty_answers.append(ans)
        analyses.extend(non_empty_answers)
        LOGGER.debug(
            f"Round {round} analyses count: {len(non_empty_answers)}\nTotal analyses count: {len(analyses)}"
        )
        round += 1
        if round >= max_rounds:
            break
        # generate new questions for the next round
        get_deeper_qns_request = {
            "api_key": api_key,
            "user_question": user_question,
            "task_type": task_type.value,
            "problem_statement": problem_statement,
            "context": context,
            "dependent_variable": dependent_variable,
            "past_analyses": analyses,
        }
        response = await make_request(
            DEFOG_BASE_URL + "/oracle/gen_explorer_qns_deeper", get_deeper_qns_request
        )
        generated_qns = response["generated_questions"]
        summary_all = response.get(
            "summary", ""
        )  # this is the summary across all analyses
    return {
        "analyses": analyses,
        "dependent_variable": dependent_variable,
        "summary": summary_all,
    }


async def explore_generated_question(
    api_key: str,
    user_question: str,
    task_type: TaskType,
    qn_id: int,
    generated_qn: str,
    dependent_variable: Dict[str, Any],
    independent_variable_group: Dict[str, Any],
    context: str,
    db_type: str,
    db_creds: Dict[str, str],
    report_chart_dir: str,
    retry_data_fetch: int,
) -> Dict[str, Any]:
    """
    Given a generated question, this function will attempt to get and run the
    necessary tools to generate the answer to this question.
    The tools include
    1) SQL generation
    2) data fetching
    3) chart generation
    4) data analysis

    Retries are attempted if the tools fail to generate the answer.

    Returns a dictionary with the following structure:
    - qn_id: int
    - generated_qn: str
    - dependent_variable: Dict[str, Any]
        - description: str
        - table.column: List[str]
    - independent_variable_group: Dict[str, Any]
        - name: str
        - description: str
        - table.column: List[str]
    - artifacts: Dict[str, Dict[str, str]]
        - outer key: str, artifact type, one of FETCHED_TABLE_CSV, TABLE_CSV, IMAGE
        - inner keys
            - artifact_content: str, e.g. csv content, image path
            - artifact_description: str, e.g. table of prices, scatter plot of x vs y
    - working: Dict[str, str]
        - generated_sql: str
        - reason_for_qn: str
        - reason_for_analysis: str
        - chart_fn_params: Dict[str, Any]
    - title: str, title of the data analysis
    - summary: str, summary of the data analysis

    Error handling policy:
    If any tool fails to generate the answer, we will log the error and the
    function will return None (for easy downstream filtering) if there isn't
    sufficiently informative data to return.

    If the data returned is empty, we will log a warning and return the minimal
    outputs for the caller to iterate on improving the generated question.
    """
    LOGGER.info(f"[Explore] {qn_id}: {generated_qn}")
    ts, timings = time.time(), []

    glossary_dict = await make_request(
        DEFOG_BASE_URL + "/prune_glossary",
        data={"question": generated_qn, "api_key": api_key},
    )
    glossary = f"{glossary_dict.get('glossary_compulsory', '')}\n{glossary_dict.get('glossary', '')}\n{context}"
    ts = save_timing(ts, f"{qn_id}\) Glossary", timings)

    err_msg, sql, data = None, None, None
    retry_count = 0
    while retry_count <= retry_data_fetch:
        # TODO: Replace gen_sql and execute_sql with XDB calls if requested in inputs
        try:
            if retry_count == 0:
                sql = await gen_sql(api_key, db_type, generated_qn, glossary)
            else:
                LOGGER.debug(f"Retrying SQL generation for {qn_id}: {generated_qn}")
                sql = await retry_sql_gen(api_key, generated_qn, sql, err_msg, db_type)
            err_msg = None
        except Exception as e:
            LOGGER.error(f"Error occurred in generating SQL: {str(e)}")
            LOGGER.error(traceback.format_exc())
            err_msg = str(e)
            sql = None
        if sql:
            # fetch data
            ts = save_timing(
                ts, f"{qn_id}\) SQL generation (try {retry_count})", timings
            )
            data, err_msg = await execute_sql(db_type, db_creds, sql)
            if err_msg == "Obtained Sorry SQL query":
                LOGGER.error(f"Sorry SQL query obtained for {qn_id}: {generated_qn}")
                break
            elif err_msg is not None:
                LOGGER.error(f"Error occurred in executing SQL: {err_msg}")
            elif isinstance(data, pd.DataFrame):
                dependent_variable_str = f"{dependent_variable['description']} ({dependent_variable['table.column']})"
                independent_variable_str = f"{independent_variable_group['description']} ({independent_variable_group['table.column']})"
                expand_sql_qn_response = await make_request(
                    DEFOG_BASE_URL + "/oracle/expand_sql_qn",
                    data={
                        "api_key": api_key,
                        "user_question": user_question,
                        "generated_qn": generated_qn,
                        "sql": sql,
                        "dependent_variable": dependent_variable_str,
                        "independent_variable": independent_variable_str,
                    },
                )
                new_sql = expand_sql_qn_response["sql"]
                new_generated_qn = expand_sql_qn_response["question"]
                if new_sql:
                    LOGGER.debug(f"Expanded SQL for {qn_id}: {generated_qn}")
                    data, err_msg = await execute_sql(db_type, db_creds, sql)
                    if err_msg is not None:
                        LOGGER.error(
                            f"Error occurred in executing expanded SQL: {err_msg}"
                        )
                    elif isinstance(data, pd.DataFrame) and not data.empty:
                        LOGGER.debug(
                            f"Data fetched after expanding SQL for {qn_id}: {generated_qn}"
                        )
                        sql = new_sql
                        generated_qn = new_generated_qn
                        break
                    else:
                        err_msg = "No data fetched"
                else:
                    err_msg = "No data fetched"
            else:
                break
        retry_count += 1
    if data is None:
        LOGGER.error(f"Data fetching failed for {qn_id}: {generated_qn}")
        return None
    ts = save_timing(ts, f"{qn_id}\) Data fetching", timings)

    # Consolidate outputs thus far for the given generated question.
    # This is the minimal output required to return, should any of the subsequent
    # tools fail.
    artifacts = {
        FETCHED_TABLE_CSV: {
            "artifact_content": data.to_csv(
                float_format="%.3f", header=True, index=False
            )
        }
    }
    outputs = {
        "qn_id": qn_id,
        "generated_qn": generated_qn,
        "independent_variable_group": {
            "name": independent_variable_group["name"],
            "description": independent_variable_group["description"],
            "table.column": independent_variable_group["table.column"],
        },
        "artifacts": artifacts,
        "working": {"generated_sql": sql},
    }

    if data.empty:
        LOGGER.error(f"No data fetched for {qn_id}: {generated_qn}")
        outputs["summary"] = "No data fetched"
        return outputs

    # choose appropriate visualization and generate chart
    chart_path = os.path.join(report_chart_dir, f"q{qn_id}.png")
    error_str = None
    try:
        dependent_variable_desc = dependent_variable["description"]
        independent_variable_desc = independent_variable_group["description"]
        chart_fn_params = await get_chart_fn(
            api_key,
            generated_qn,
            data,
            dependent_variable_desc,
            independent_variable_desc,
        )
        run_chart_fn(chart_fn_params, data, chart_path)
        # TODO inspect the chart visually by sending it to a VLM for ensuring
        # that the chart is meaningful (not too cluttered, too many categories
        # in the legend, etc)
    except Exception as e:
        error_str = str(e) + "\n" + traceback.format_exc()
        LOGGER.error(f"Error occurred in during chart generation: {error_str}")
    tries = 0
    while error_str and tries < RETRY_CHART_GEN:
        # TODO call retry chart generation endpoint, update chart_fn_params, retry run_chart_fn
        tries += 1
    if not os.path.exists(chart_path):
        LOGGER.error(f"Chart could not be generated for {qn_id}: {generated_qn}")
        return outputs
    # save chosen chart function and arguments
    outputs["working"]["chart_fn_params"] = chart_fn_params
    # add the data represented in the chart to the artifacts
    chart_df = get_chart_df(data, chart_fn_params)
    artifacts[TABLE_CSV] = {
        "artifact_content": chart_df.to_csv(
            float_format="%.3f", header=True, index=False
        )
    }
    ts = save_timing(ts, f"{qn_id}\) Get and Plot chart", timings)

    # TODO: DEF-552 add retries for chart plotting based on error type and if chart
    # visuals are not meaningful (e.g. axis labels overlap, no data points, etc)

    # add chart to outputs
    artifacts[IMAGE] = {"artifact_location": chart_path}

    # we get the anomalies from the raw data, not the chart data
    anomalies_df = get_anomalies(data, chart_fn_params)
    LOGGER.debug(f"Anomalies {anomalies_df}")
    if anomalies_df is not None:
        LOGGER.debug(f"Anomalies found for {qn_id}: {generated_qn}")
        artifacts[ANOMALIES_CSV] = {
            "artifact_content": anomalies_df.to_csv(
                float_format="%.3f", header=True, index=False
            )
        }

    correlation_dict = get_correlation(chart_df, chart_fn_params)
    if correlation_dict is not None:
        corr = correlation_dict["correlation"]
        x_col = correlation_dict["x_col"]
        y_col = correlation_dict["y_col"]
        LOGGER.debug(f"Correlation between {x_col} and {y_col}: {corr}")
        artifacts[CORRELATION] = {
            "artifact_content": f"{corr:.3f}",
            "artifact_description": f"Correlation between {x_col} and {y_col}"
        }

    # generate data analysis
    try:
        data_analysis = await gen_data_analysis(
            task_type,
            api_key,
            generated_qn,
            sql,
            chart_df,
            anomalies_df,
            correlation_dict,
            chart_fn_params,
        )
        if "error" in data_analysis and data_analysis["error"]:
            LOGGER.error(
                f"Error occurred in generating data analysis: {data_analysis['error']}"
            )
            return outputs
    except Exception as e:
        LOGGER.error(f"Error occurred in generating data analysis: {str(e)}")
        LOGGER.error(traceback.format_exc())
        return outputs  # return minimal outputs if data analysis fails
    ts = save_timing(ts, f"{qn_id}\) Data analysis", timings)

    # add title and summary to outputs
    outputs["title"] = data_analysis["title"]
    outputs["summary"] = data_analysis["summary"]
    # add table and image descriptions to artifacts if available
    if TABLE_CSV in artifacts:
        if "table_description" in data_analysis:
            artifacts[TABLE_CSV]["artifact_description"] = data_analysis[
                "table_description"
            ]
        else:
            LOGGER.warning(
                f"Table description not generated for {qn_id}: {generated_qn}"
            )
    if IMAGE in artifacts:
        if "image_description" in data_analysis:
            artifacts[IMAGE]["artifact_description"] = data_analysis[
                "image_description"
            ]
        else:
            LOGGER.warning(
                f"Image description not generated for {qn_id}: {generated_qn}"
            )
    ts = save_timing(ts, f"{qn_id}\) Consolidate outputs", timings)

    LOGGER.info(
        f"[Explore] {qn_id}: {generated_qn} completed in {time.time() - ts:.2f}s"
    )
    return outputs
