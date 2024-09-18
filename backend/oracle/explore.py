import asyncio
import os
import time
import traceback
from typing import Any, Dict

from db_utils import get_db_type_creds
from generic_utils import make_request
from utils_logging import LOGGER, save_timing
from oracle.utils_explore_data import (
    TABLE_CSV,
    IMAGE,
    gen_sql,
    execute_sql,
    get_chart_type,
    plot_chart,
    gen_data_analysis,
)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


async def explore_data(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
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
    LOGGER.info(f"Exploring data for report {report_id}")
    LOGGER.info(f"Task type: {task_type}")
    user_question = inputs["user_question"]
    gather_context = outputs["gather_context"]
    context = gather_context.get("context", "")
    problem_statement = gather_context.get("problem_statement", "")
    glossary_dict = await make_request(
        DEFOG_BASE_URL + "/prune_glossary",
        data={"question": user_question, "api_key": api_key},
    )
    glossary = f"{glossary_dict.get('glossary_compulsory', '')}\n{glossary_dict.get('glossary', '')}\n{context}"
    db_type, db_creds = get_db_type_creds(api_key)
    LOGGER.info(f"DB type: {db_type}")
    LOGGER.info(f"DB creds: {db_creds}")

    # create the directory to save the chart
    current_dir = os.getcwd()
    report_chart_dir = os.path.join(
        current_dir, f"oracle/reports/{api_key}/report_{report_id}"
    )
    os.makedirs(report_chart_dir, exist_ok=True)

    # generate explorer questions
    json_data = {
        "api_key": api_key,
        "user_question": user_question,
        "n_gen_qns": 10,
        "task_type": task_type,
        "gather_context": gather_context,
    }
    LOGGER.info(f"Generating explorer questions")
    generated_qns = await make_request(
        DEFOG_BASE_URL + "/oracle/gen_explorer_qns", json_data
    )
    if "error" in generated_qns:
        LOGGER.error(
            f"Error occurred in generating explorer questions: {generated_qns['error']}"
        )
        return None

    # TODO add additional input format checks and retries
    generated_qns = generated_qns.get("generated_questions", [])
    LOGGER.info(f"Generated questions: {generated_qns}\n")

    generated_qns = [
        q for q in generated_qns if q.get("data_available", False) and "question" in q
    ]  # remove questions where data_available is False
    generated_qns = sorted(
        generated_qns, key=lambda x: x["relevancy_score"], reverse=True
    )  # sort questions by relevancy score

    final_analyses = []
    max_analyses = 5
    qn_id = 0
    while (
        len(final_analyses) < max_analyses and len(generated_qns) > 0
    ):  # terminated when max_analyses is reached or all generated_qns are exhausted
        # get the top k questions from generated_qns
        k = min(max_analyses, len(generated_qns), max_analyses - len(final_analyses))
        topk_qns = generated_qns[:k]

        # explore the top k questions
        tasks = []
        for q in topk_qns:
            tasks.append(
                explore_generated_question(
                    api_key,
                    user_question,
                    qn_id,
                    q["question"],
                    glossary,
                    db_type,
                    db_creds,
                    report_chart_dir,
                )
            )
            qn_id += 1
        topk_answers = await asyncio.gather(*tasks)
        # remove None answers
        analyses_for_eval = [ans for ans in topk_answers if ans is not None]
        LOGGER.debug(f"Analyses for evaluation count: {len(analyses_for_eval)}")

        # evaluate the analyses sequentially
        final_summaries = []
        for analysis in analyses_for_eval:
            final_summaries_str = "\n".join(
                f"{i + 1}. {summary}" for i, summary in enumerate(final_summaries)
            )

            json_data = {
                "api_key": api_key,
                "user_question": user_question,
                "problem_statement": problem_statement,
                "generated_qn": analysis["generated_qn"],
                "final_summaries_str": final_summaries_str,
            }
            if "summary" in analysis:
                json_data["summary"] = analysis["summary"]
            resp = await make_request(
                f"{DEFOG_BASE_URL}/oracle/eval_explorer_data_analysis", data=json_data
            )
            if "error" in resp:
                LOGGER.error(f"Error occurred in evaluating analysis: {resp['error']}")
                continue
            reason = resp.get("reason", "")
            usefulness = resp.get("usefulness", False)
            newness = resp.get("newness", False)
            LOGGER.info(
                f"Generated question: {analysis['generated_qn']}, Reason: {reason}, Usefulness: {usefulness}, Newness: {newness}\n"
            )
            if usefulness and newness:
                if "evaluation" not in analysis:
                    analysis["evaluation"] = {}
                analysis["evaluation"]["analysis_usefulness"] = usefulness
                analysis["evaluation"]["analysis_newness"] = newness
                analysis["working"]["reason_for_analysis_eval"] = reason
                final_summaries.append(analysis["summary"])
                final_analyses.append(analysis)
                if len(final_analyses) >= max_analyses:
                    break

        # add analysis_id to final_analyses
        for i, analysis in enumerate(final_analyses):
            analysis["analysis_id"] = i + 1

        # TODO evaluate quality and quantity of information gathered so far and
        # add more questions for processing if needed

    LOGGER.info(f"Final analyses count: {len(final_analyses)}\n{final_analyses}")
    return final_analyses


async def explore_generated_question(
    api_key: str,
    user_question: str,
    qn_id: int,
    generated_qn: str,
    glossary: str,
    db_type: str,
    db_creds: Dict[str, str],
    report_chart_dir: str,
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
    - artifacts: Dict[str, Dict[str, str]]
        - outer key: str, artifact type, one of TABLE_CSV, IMAGE
        - inner keys
            - artifact_content: str, e.g. csv content, image path
            - artifact_description: str, e.g. table of prices, scatter plot of x vs y
    - working: Dict[str, str]
        - generated_sql: str
        - reason_for_qn: str
        - reason_for_analysis: str
    - title: str, title of the data analysis
    - summary: str, summary of the data analysis

    Error handling policy:
    If any tool fails to generate the answer, we will log the error and the
    function will return None (for easy downstream filtering). We err on the side
    of
    """
    LOGGER.info(f"[Explore] {qn_id}: {generated_qn}")
    ts, timings = time.time(), []
    # generate SQL
    try:
        sql = await gen_sql(api_key, db_type, generated_qn, glossary)
    except Exception as e:
        LOGGER.error(f"Error occurred in generating SQL: {str(e)}")
        LOGGER.error(traceback.format_exc())
        sql = None
    if not sql:
        return None
    # fetch data
    ts = save_timing(ts, f"{qn_id}) SQL generation", timings)

    # TODO generate SQL across multiple DB's and stitch them together with pandas

    try:
        data = await execute_sql(api_key, db_type, db_creds, generated_qn, sql)
    except Exception as e:
        LOGGER.error(f"Error occurred in fetching data: {str(e)}")
        LOGGER.error(traceback.format_exc())
        data = None
    if data is None:
        return None
    ts = save_timing(ts, f"{qn_id}) Data fetching", timings)

    # TODO add retries for SQL gen + data fetching based on error type/empty data
    # we will have to wrap the SQL gen and data fetching in a retry loop

    # choose appropriate visualization
    try:
        chart_type = await get_chart_type(api_key, data.columns.to_list(), generated_qn)
    except Exception as e:
        LOGGER.error(f"Error occurred in getting chart type: {str(e)}")
        LOGGER.error(traceback.format_exc())
        chart_type = None
    if not chart_type:
        return None
    ts = save_timing(ts, f"{qn_id}) Get chart type", timings)

    # Consolidate outputs thus far for the given generated question.
    # This is the minimal output required to return, should any of the subsequent
    # tools fail.
    artifacts = {
        TABLE_CSV: {
            "artifact_content": data.to_csv(
                float_format="%.3f", header=True, index=False
            )
        }
    }
    outputs = {
        "qn_id": qn_id,
        "generated_qn": generated_qn,
        "artifacts": artifacts,
        "working": {"generated_sql": sql},
    }

    # generate chart
    try:
        chart_path = await plot_chart(
            report_chart_dir,
            data,
            chart_type["chart_type"],
            chart_type.get("xAxisColumns", []),
            chart_type.get("yAxisColumns", []),
        )
    except Exception as e:
        LOGGER.error(f"Error occurred in plotting chart: {str(e)}")
        LOGGER.error(traceback.format_exc())
        chart_path = None
    if not chart_path:
        return outputs  # return minimal outputs if chart generation fails
    ts = save_timing(ts, f"{qn_id}) Plot chart", timings)

    # TODO add retries for chart plotting based on error type and if chart
    # visuals are not meaningful (e.g. axis labels overlap, no data points, etc)

    # add chart to outputs
    artifacts[IMAGE] = {"artifact_location": chart_path}

    # generate data analysis
    try:
        data_analysis = await gen_data_analysis(
            api_key, user_question, generated_qn, sql, data, chart_path
        )
    except Exception as e:
        LOGGER.error(f"Error occurred in generating data analysis: {str(e)}")
        LOGGER.error(traceback.format_exc())
        return outputs  # return minimal outputs if data analysis fails
    ts = save_timing(ts, f"{qn_id}) Data analysis", timings)

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
    ts = save_timing(ts, f"{qn_id}) Consolidate outputs", timings)

    LOGGER.info(
        f"[Explore] {qn_id}: {generated_qn} completed in {time.time() - ts:.2f}s"
    )
    return outputs
