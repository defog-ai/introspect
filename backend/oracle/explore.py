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
    get_chart_fn,
    gen_data_analysis,
    retry_sql_gen,
    run_chart_fn,
)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
MAX_ANALYSES = 5
MAX_ROUNDS = 2
RETRY_DATA_FETCH = 1
RETRY_CHART_GEN = 1


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
        "n_gen_qns": inputs.get("max_analyses", MAX_ANALYSES),
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

    generated_qns = [
        q for q in generated_qns if q.get("data_available", False) and "question" in q
    ]  # remove questions where data_available is False
    generated_qns = sorted(
        generated_qns, key=lambda x: x["relevancy_score"], reverse=True
    )  # sort questions by relevancy score

    LOGGER.debug(f"Generated questions with data: {len(generated_qns)}")

    final_analyses = []
    final_summaries = []
    max_analyses = inputs.get("max_analyses", MAX_ANALYSES)
    # increments by 1 for each round of while loop
    max_rounds = inputs.get("max_rounds", MAX_ROUNDS)
    qn_id = 0
    round_count = 0
    while (
        len(final_analyses) < max_analyses
        and len(generated_qns) > 0
        and round_count < max_rounds
    ):
        LOGGER.debug(f"Round {round_count} started")
        tasks = []
        for q in generated_qns:
            # question used by 1st round question generation
            if "question" in q:
                qn = q["question"]
            else:
                LOGGER.error(f"Question not found in {q}")
                continue
            tasks.append(
                explore_generated_question(
                    api_key,
                    user_question,
                    qn_id,
                    qn,
                    context,
                    db_type,
                    db_creds,
                    report_chart_dir,
                    inputs.get("retry_data_fetch", RETRY_DATA_FETCH),
                )
            )
            qn_id += 1
        topk_answers = await asyncio.gather(*tasks)
        # remove None answers
        analyses_for_eval = [ans for ans in topk_answers if ans is not None]
        LOGGER.debug(f"Analyses for evaluation count: {len(analyses_for_eval)}")

        # evaluate the analyses sequentially to check for usefulness and newness
        unfit_analyses = []
        for analysis in analyses_for_eval:
            if "summary" not in analysis:
                unfit_analyses.append(analysis)
                continue
            final_summaries_str = "\n".join(
                f"{i + 1}. {summary}" for i, summary in enumerate(final_summaries)
            )

            json_data = {
                "api_key": api_key,
                "user_question": user_question,
                "problem_statement": problem_statement,
                "generated_qn": analysis["generated_qn"],
                "summary": analysis["summary"],
                "final_summaries_str": final_summaries_str,
            }
            resp = await make_request(
                f"{DEFOG_BASE_URL}/oracle/eval_explorer_data_analysis", data=json_data
            )
            if "error" in resp:
                LOGGER.error(f"Error occurred in evaluating analysis: {resp['error']}")
                continue
            reason = resp.get("reason", "")
            usefulness = resp.get("usefulness", False)
            newness = resp.get("newness", False)
            LOGGER.debug(
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
            else:
                unfit_analyses.append(analysis)

        # break if we have achieved the number of analyses required
        if len(final_analyses) >= max_analyses:
            break

        # generate more questions if needed
        json_data = {
            "api_key": api_key,
            "user_question": user_question,
            "task_type": task_type,
            "previous_questions": final_analyses + unfit_analyses,
            "gather_context": gather_context,
        }
        resp = await make_request(
            f"{DEFOG_BASE_URL}/oracle/regen_explorer_qns", data=json_data
        )
        answered_questions = resp.get("answered_questions", [])
        final_analyses_ordered = []
        for q in answered_questions:
            for ans in final_analyses:
                if ans["generated_qn"] == q:
                    final_analyses_ordered.append(ans)
                    break
        final_analyses = final_analyses_ordered
        generated_qns = resp.get("refined_questions", [])
        LOGGER.debug(f"Round {round_count} end")
        round_count += 1

    LOGGER.debug(f"Final analyses count: {len(final_analyses)}\n{final_analyses}")
    return final_analyses


async def explore_generated_question(
    api_key: str,
    user_question: str,
    qn_id: int,
    generated_qn: str,
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
    ts = save_timing(ts, f"{qn_id}) Glossary", timings)

    err_msg, sql, data = None, None, None
    retry_count = 0
    while retry_count < retry_data_fetch:
        # TODO: DEF-540 generate SQL across multiple DB's and stitch them together with pandas
        # generate SQL
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
                ts, f"{qn_id}) SQL generation (try {retry_count})", timings
            )
            try:
                data = await execute_sql(db_type, db_creds, generated_qn, sql)
                err_msg = None
                break
            except Exception as e:
                LOGGER.error(f"Error occurred in fetching data: {str(e)}")
                LOGGER.error(traceback.format_exc())
                err_msg = str(e)
                data = None
        retry_count += 1
    if data is None:
        LOGGER.error(f"Data fetching failed for {qn_id}: {generated_qn}")
        return None
    ts = save_timing(ts, f"{qn_id}) Data fetching", timings)

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

    if data.empty:
        LOGGER.error(f"No data fetched for {qn_id}: {generated_qn}")
        return outputs

    # choose appropriate visualization and generate chart
    chart_path = os.path.join(report_chart_dir, f"q{qn_id}.png")
    error_str = None
    try:
        chart_fn_params = await get_chart_fn(api_key, generated_qn, data)
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

    ts = save_timing(ts, f"{qn_id}) Get and Plot chart", timings)

    # TODO: DEF-552 add retries for chart plotting based on error type and if chart
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
