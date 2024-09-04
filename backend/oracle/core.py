import asyncio
import json
import os
import pandas as pd
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List

from celery.utils.log import get_task_logger
from db_utils import OracleReports, OracleSources, engine, get_db_type_creds
from generic_utils import make_request
from markdown_pdf import MarkdownPdf, Section
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from utils_logging import LOG_LEVEL, save_and_log, save_timing
from utils_md import mk_create_table_ddl
from .utils_explore_data import gen_sql, execute_sql, get_chart_type, plot_chart, gen_data_analysis

from .celery_app import celery_app

EXPLORATION = "exploration"
PREDICTION = "prediction"
OPTIMIZATION = "optimization"
TASK_TYPES = [
    EXPLORATION,
    PREDICTION,
    OPTIMIZATION,
]
DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
# celery requires a different logger object. we can still reuse utils_logging
# which just assumes a LOGGER object is defined
LOGGER = get_task_logger(__name__)
LOGGER.setLevel(LOG_LEVEL)

celery_async_executors = ThreadPoolExecutor(max_workers=4)


@celery_app.task
def begin_generation_task(
    api_key: str, username: str, report_id: int, task_type: str, inputs: Dict[str, Any]
):
    t_start = datetime.now()
    LOGGER.info(f"Starting celery task for {username} at {t_start}")
    with celery_async_executors:
        loop = asyncio.get_event_loop()
        task = loop.create_task(
            begin_generation_async_task(api_key, username, report_id, task_type, inputs)
        )
        loop.run_until_complete(task)
    t_end = datetime.now()
    time_elapsed = (t_end - t_start).total_seconds()
    LOGGER.info(f"Completed celery task for {username} in {time_elapsed:.2f} seconds.")


async def begin_generation_async_task(
    api_key: str, username: str, report_id: int, task_type: str, inputs: Dict[str, Any]
):
    """
    This is the entry point for the oracle, which will kick off the control flow,
    by starting the first stage of the report generation process.
    This function call is long-running, and will not return immediately.
    It will await on the next stage to be completed before proceeding to the next stage.
    It will only return when the report is done, or an error has occurred.

    Every call to control is scoped over a single report_id, which can only
    belong to 1 api_key and username.
    """
    stage = "gather_context"
    outputs = {}
    continue_generation = True
    ts, timings = time.time(), []

    while continue_generation:
        # call the control function with the current stage
        try:
            LOGGER.info(f"Executing stage {stage} for report {report_id}")
            stage_result = await execute_stage(
                api_key=api_key,
                username=username,
                report_id=report_id,
                task_type=task_type,
                stage=stage,
                inputs=inputs,
                outputs=outputs,
            )
            outputs[stage] = stage_result
            # update the status and current outputs of the report generation
            with Session(engine) as session:
                stmt = select(OracleReports).where(OracleReports.report_id == report_id)
                result = session.execute(stmt)
                report = result.scalar_one()
                report.status = stage
                report.outputs = outputs
                session.commit()
        except Exception as e:
            LOGGER.error(f"Error occurred in stage {stage}:\n{e}")
            # print traceback of exception
            LOGGER.error(traceback.format_exc())
            # update the status of the report
            with Session(engine) as session:
                stmt = select(OracleReports).where(OracleReports.report_id == report_id)
                result = session.execute(stmt)
                report = result.scalar_one()
                report.status = "error"
                session.commit()
            continue_generation = False
        
        if stage == "done":
            continue_generation = False
        # perform logging for current stage
        if continue_generation:
            ts = save_timing(ts, f"Stage {stage} completed", timings)
            stage = next_stage(stage, task_type)
        else:
            save_and_log(ts, f"Report {report_id} completed", timings)


def next_stage(stage: str, task_type: str) -> str:
    if stage == "gather_context":
        return "wait_clarifications"
    elif stage == "wait_clarifications":
        return "explore"
    elif stage == "explore":
        if task_type == EXPLORATION:
            return "export"
        elif task_type == PREDICTION:
            return "predict"
        elif task_type == OPTIMIZATION:
            return "optimize"
    elif stage == "predict" and task_type == PREDICTION:
        return "export"
    elif stage == "optimize" and task_type == OPTIMIZATION:
        return "export"
    elif stage == "export":
        return "done"
    else:
        raise ValueError(f"Stage {stage} not recognized.")


async def execute_stage(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    stage: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    Depending on the current stage, the control function will call the appropriate
    function to handle the stage. The stage functions will perform the necessary
    actions to complete the stage and return the result.
    We prefer explicit function references rather than calling `exec` or `eval`
    over the same set of input arguments to facilitate easier reading and also 
    for security reasons.
    """
    if stage == "gather_context":
        stage_result = await gather_context(
            api_key=api_key,
            username=username,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == "explore":
        stage_result = await explore_data(
            api_key=api_key,
            username=username,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == "wait_clarifications":
        stage_result = await wait_clarifications(
            api_key=api_key,
            username=username,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == "predict":
        stage_result = await predict(
            api_key=api_key,
            username=username,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == "optimize":
        stage_result = await optimize(
            api_key=api_key,
            username=username,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == "export":
        stage_result = await export(
            api_key=api_key,
            username=username,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == "done":
        stage_result = None
    # add more stages here for new report sections if necessary in the future
    else:
        raise ValueError(f"Stage {stage} not recognized.")
    return stage_result


async def gather_context(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will gather the context for the report, by consolidating
    information from the glossary, metadata, and unstructured data sources,
    which are relevant to the question and metric_sql provided.

    One of the key side effects is that it will save the tables from the parsed
    sources into the database, creating new tables, and updating the metadata
    in the backend with the new metadata.
    
    Returns a dictionary with the following outputs:
    
    Always present across task types:
    - problem_statement: str. The summarized brief of the problem at hand to solve. first to be generated.
    - context: str. The context of the problem, described qualitatively. second to be generated.
    - issues: List[str]. A list of issues with the data. empty list returned if no issues present. last to be generated.

    Exploration task type:
    - data_overview: str. A brief overview of the data.

    Prediction task type:
    - target: str. The target variable to predict.
    - features: List[str]. A list of features to use for prediction.

    Optimization task type:
    - objective: str. The objective of the optimization.
    - constraints: List[str]. A list of constraints for the formulation.
    - variables: List[str]. A list of decision variables that the user can control.
    """
    ts, timings = time.time(), []
    LOGGER.debug(f"Gathering context for report {report_id}")
    user_question = inputs["user_question"]
    LOGGER.debug("Got the following sources:")
    sources = []
    for source in inputs["sources"]:
        if "link" in source:
            source["type"] = "webpage"
            sources.append(source)
        LOGGER.debug(f"{source}")
    json_data = {
        "api_key": api_key,
        "user_question": user_question,
        "sources": sources,
    }
    # each source now contains "text" and "summary" keys
    sources_parsed = await make_request(
        DEFOG_BASE_URL + "/unstructured_data/parse", json_data
    )
    sources_to_insert = []
    for source in sources_parsed:
        attributes = source.get("attributes")
        if isinstance(attributes, Dict) or isinstance(attributes, List):
            attributes = json.dumps(attributes)
        source_to_insert = {
            "link": source["link"],
            "title": source.get("title", ""),
            "position": source.get("position"),
            "source_type": source.get("type"),
            "attributes": attributes,
            "snippet": source.get("snippet"),
            "text_parsed": source.get("text"),
            "text_summary": source.get("summary"),
        }
        sources_to_insert.append(source_to_insert)
    with Session(engine) as session:
        # insert the sources into the database if not present. otherwise update
        for source in sources_to_insert:
            stmt = select(OracleSources).where(OracleSources.link == source["link"])
            result = session.execute(stmt)
            if result.scalar() is None:
                stmt = insert(OracleSources).values(source)
                session.execute(stmt)
                LOGGER.debug(f"Inserted source {source['link']} into the database.")
            else:
                stmt = (
                    update(OracleSources)
                    .where(OracleSources.link == source["link"])
                    .values(source)
                )
                session.execute(stmt)
                LOGGER.debug(f"Updated source {source['link']} in the database.")
        session.commit()
    LOGGER.debug(f"Inserted {len(sources_to_insert)} sources into the database.")
    ts = save_timing(ts, "Sources parsed", timings)

    tables = [table for source in sources_parsed if "tables" in source for table in source["tables"]]
    parse_table_tasks = []
    for table in tables:
        table_data = {
            "api_key": api_key,
            "all_rows": [table["column_names"]] + table["rows"],
            "previous_text": table.get("previous_text"),
        }
        parse_table_tasks.append(make_request(DEFOG_BASE_URL + "/unstructured_data/infer_table_properties", table_data))
    parsed_tables = await asyncio.gather(*parse_table_tasks)
    inserted_tables = {}
    with engine.connect() as connection:
        for parsed_table in parsed_tables:
            try:
                if "table_name" not in parsed_table:
                    LOGGER.error("No table name found in parsed table.")
                    continue
                table_name = parsed_table["table_name"]
                if "columns" not in parsed_table:
                    LOGGER.error(f"No columns found in parsed table {table_name}.")
                    continue
                columns = parsed_table["columns"]
                column_names = [column["column_name"] for column in columns]
                num_cols = len(columns)
                if "rows" not in parsed_table:
                    LOGGER.error(f"No rows found in parsed table {table_name}.")
                    continue
                rows = parsed_table["rows"] # 2D list of data
                create_table_ddl = mk_create_table_ddl(table_name, columns)
                connection.execute(create_table_ddl)
                LOGGER.info(f"Created table {table_name} in the database.")
                insert_stmt = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(['%s'] * num_cols)})"
                for i, row in enumerate(rows):
                    # check if the row has the correct number of columns
                    if len(row) != num_cols:
                        LOGGER.error(f"Row {i} has {len(row)} columns, but expected {num_cols}. Skipping row.\n{row}")
                connection.execute(insert_stmt, rows)
                LOGGER.info(f"Inserted {len(rows)} rows into table {table_name}.")
                inserted_tables[table_name] = columns
            except Exception as e:
                LOGGER.error(f"Error occurred in parsing table: {e}\n{traceback.format_exc()}")
    ts = save_timing(ts, "Tables saved", timings)
    # get and update metadata
    response = await make_request(DEFOG_BASE_URL + "/get_metadata", {"api_key": api_key})
    md = response.get("table_metadata", {})
    md.update(inserted_tables)
    response = await make_request(DEFOG_BASE_URL + "/update_metadata", {"api_key": api_key, "table_metadata": md})
    LOGGER.info(f"Updated metadata for api_key {api_key}")
    ts = save_timing(ts, "Metadata updated", timings)

    
    # summarize all sources. we only need the title, type, and summary
    sources_summary = []
    for source in sources_parsed:
        source_summary = {
            "title": source.get("title", ""),
            "type": source.get("type"),
            "summary": source.get("summary"),
        }
        sources_summary.append(source_summary)
    json_data = {
        "api_key": api_key,
        "user_question": user_question,
        "task_type": task_type,
        "sources": sources_summary,
    }
    combined_summary = await make_request(
        DEFOG_BASE_URL + "/unstructured_data/combine_summaries", json_data
    )
    if "error" in combined_summary:
        LOGGER.error(f"Error occurred in combining summaries: {combined_summary['error']}")
        return

    # validate response from backend
    if "problem_statement" not in combined_summary:
        LOGGER.error("No problem statement found in combined summary.")
    if "context" not in combined_summary:
        LOGGER.error("No context found in combined summary.")
    if "issues" not in combined_summary:
        LOGGER.error("No issues found in combined summary.")
    if task_type == EXPLORATION:
        if "data_overview" not in combined_summary:
            LOGGER.error("No data overview found in combined summary.")
    elif task_type == PREDICTION:
        if "target" not in combined_summary:
            LOGGER.error("No target found in combined summary.")
        if "features" not in combined_summary:
            LOGGER.error("No features found in combined summary.")
    elif task_type == OPTIMIZATION:
        if "objective" not in combined_summary:
            LOGGER.error("No objective found in combined summary.")
        if "constraints" not in combined_summary:
            LOGGER.error("No constraints found in combined summary.")
        if "variables" not in combined_summary:
            LOGGER.error("No variables found in combined summary.")
    LOGGER.debug(f"Context gathered for report {report_id}:\n{combined_summary}")
    save_and_log(ts, "Combined summary", timings)
    return combined_summary


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
    - artifacts: List[Dict[str, str]]
        - artifact_type: str, e.g. table csv, image
        - artifact_content: str, e.g. csv content, image path
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
    glossary_dict = await make_request(DEFOG_BASE_URL + "/prune_glossary", json={"question": user_question, "api_key": api_key})
    glossary = f"{glossary_dict.get('glossary_compulsory', '')}\n{glossary_dict.get('glossary', '')}\n{context}"
    db_type, db_creds = get_db_type_creds(api_key)
    LOGGER.info(f"DB type: {db_type}")
    LOGGER.info(f"DB creds: {db_creds}")

    # generate explorer questions
    json_data = {
                "api_key": api_key,
                "user_question": user_question,
                "n_gen_qns": 10,
                "task_type": task_type,
                "gather_context": gather_context,
            }
    LOGGER.info(f"Generating explorer questions")
    generated_qns = await make_request(DEFOG_BASE_URL + "/oracle/gen_explorer_qns", json_data)
    if "error" in generated_qns:
        LOGGER.error(f"Error occurred in generating explorer questions: {generated_qns['error']}")
        return
    generated_qns = generated_qns["generated_questions"]
    LOGGER.info(f"Generated questions: {generated_qns}\n")
    
    generated_qns = [q for q in generated_qns if q["data_available"]]  # remove questions where data_available is False
    generated_qns = sorted(generated_qns, key=lambda x: x["relevancy_score"], reverse=True)  # sort questions by relevancy score

    final_analyses = []
    max_analyses = 5
    while len(final_analyses) < max_analyses and len(generated_qns) > 0: # terminated when max_analyses is reached or all generated_qns are exhausted
        # get the top k questions from generated_qns
        k = min(max_analyses, len(generated_qns), max_analyses - len(final_analyses))
        topk_qns = generated_qns[:k]
        generated_qns = generated_qns[k:]
        
        LOGGER.info(f"Generating SQL for {len(topk_qns)} questions")
        # generate SQL for each question concurrently
        gen_sql_tasks = [gen_sql(api_key, db_type, q["question"], glossary) for q in topk_qns]
        topk_sqls = await asyncio.gather(*gen_sql_tasks)
        # filter out questions/sql where sql is not generated
        filtered_data = [(q, sql) for q, sql in zip(topk_qns, topk_sqls) if sql is not None]
        if filtered_data:
            topk_qns, topk_sqls = zip(*filtered_data)
        else:
            continue

        # fetch data in dataframes for each SQL query concurrently
        exec_sql_tasks = [execute_sql(api_key, db_type, db_creds, q["question"], sql) for q, sql in zip(topk_qns, topk_sqls)] #TODO: add execute_sql within db_utils instead of using defog python library
        topk_data = await asyncio.gather(*exec_sql_tasks)
        LOGGER.info(f"Data fetched from client's DB: {topk_data}\n")
        # filter out questions/sql/data where data is not an empty dataframe
        filtered_data = [(q, sql, data) for q, sql, data in zip(topk_qns, topk_sqls, topk_data) if data is not None and not data.empty]
        if filtered_data:
            topk_qns, topk_sqls, topk_data = zip(*filtered_data)
        else:
            continue

        # choose appropriate visualization for each question
        get_chart_type_tasks = [get_chart_type(api_key, data.columns.to_list(),  q["question"]) for q, data in zip(topk_qns, topk_data)]
        topk_chart_types = await asyncio.gather(*get_chart_type_tasks)
        LOGGER.info(f"Suitable chart types: {topk_chart_types}\n")

        # generate charts for each question concurrently TODO: add more supported chart types
        plot_chart_tasks = [plot_chart(api_key, report_id, data, chart_type["chart_type"], chart_type["xAxisColumns"], chart_type["yAxisColumns"]) for data, chart_type in zip(topk_data, topk_chart_types)]
        topk_chart_paths = await asyncio.gather(*plot_chart_tasks)
        LOGGER.info(f"Chart paths: {topk_chart_paths}\n")

        # generate data analyses concurrently
        gen_data_analysis_tasks = [gen_data_analysis(api_key, user_question, q["question"], data, chart_path) for q, data, chart_path in zip(topk_qns, topk_data, topk_chart_paths)]
        topk_data_analyses = await asyncio.gather(*gen_data_analysis_tasks)
        # filter out questions/sql/data/chart/analyses where data analysis is not generated
        filtered_data = [(q, sql, data, chart_path, data_analysis) for q, sql, data, chart_path, data_analysis in zip(topk_qns, topk_sqls, topk_data, topk_chart_paths, topk_data_analyses) if data_analysis["title"] is not None]
        if filtered_data:
            topk_qns, topk_sqls, topk_data, topk_chart_paths, topk_data_analyses = zip(*filtered_data)
        LOGGER.info(f"Data analyses: {topk_data_analyses}\n")

        # package the question, sql, data, chart, and data analysis
        analyses_for_eval = []
        analyses_for_eval.extend(
            [
                {
                    "analysis_id": None,
                    "generated_qn": q["question"],
                    "artifacts": [
                        {
                            "artifact_type": "table csv",
                            "artifact_content": data.to_csv(float_format="%.3f", header=True),
                        },
                        {
                            "artifact_type": "image",
                            "artifact_location": chart_path,
                        },
                    ],
                    "working": {
                        "generated_sql": sql,
                        "reason_for_qn": q["reason"],
                    },

                    "title": data_analysis["title"],
                    "summary": data_analysis["summary"],
                    "evaluation": {
                        "qn_relevance": q["relevancy_score"],
                    }
                }
                for q, sql, data, chart_path, data_analysis in zip(topk_qns, topk_sqls, topk_data, topk_chart_paths, topk_data_analyses)
            ]
        )
        LOGGER.info(f"Analyses for evaluation count: {len(analyses_for_eval)}")

        # evaluate the analyses sequentially 
        final_summaries = []
        for analysis in analyses_for_eval:
            final_summaries_str = "\n".join(f"{i + 1}. {summary}" for i, summary in enumerate(final_summaries))

            json_data = {
                "api_key": api_key,
                "user_question": user_question,
                "problem_statement": problem_statement,
                "generated_qn": analysis["generated_qn"],
                "summary": analysis["summary"],
                "final_summaries_str": final_summaries_str,
            }
            resp = await make_request(f"{DEFOG_BASE_URL}/oracle/eval_explorer_data_analysis", json=json_data)
            if "error" in resp:
                LOGGER.error(f"Error occurred in evaluating analysis: {resp['error']}")
                continue
            reason = resp.get("reason", "")
            usefulness = resp.get("usefulness", False)
            newness = resp.get("newness", False)
            LOGGER.info(f"Generated question: {analysis['generated_qn']}, Reason: {reason}, Usefulness: {usefulness}, Newness: {newness}\n")
            if usefulness and newness:
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

    LOGGER.info(f"Final analyses count: {len(final_analyses)}\n{final_analyses}")
    return final_analyses


async def wait_clarifications(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will check the `clarifications` table in the SQLite3 database,
    polling every x seconds to see if all the clarifications for a given
    `report_id` have been addressed before proceeding to the next stage.
    """
    # TODO implement this function
    # dummy print statement for now
    LOGGER.info(f"Waiting for clarifications for report {report_id}")
    # sleep for a random amount of time to simulate work
    await asyncio.sleep(random.random() * 2)
    return {"clarifications": "all clarifications addressed"}


async def predict(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will make the necessary predictions, by training a machine learning
    model on the data provided, and generating predictions needed for the analysis.
    Intermediate model and predictions generated will be saved in the report_id's
    directory.
    """
    # TODO implement this function
    # dummy print statement for now
    LOGGER.info(f"Predicting for report {report_id}")
    # sleep for a random amount of time to simulate work
    await asyncio.sleep(random.random() * 2)
    return {"predictions": "predictions generated"}


async def optimize(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will optimize the objective input by the user, considering
    the context, data, and predictions generated. We will formulate the optimization
    problem as a linear program, solve it using a solver, and return the optimal
    solution(s) or infeasibility if found.
    """
    # TODO implement this function
    # dummy print statement for now
    LOGGER.info(f"Optimizing for report {report_id}")
    # sleep for a random amount of time to simulate work
    await asyncio.sleep(random.random() * 2)
    return {"optimization": "optimization completed"}


async def export(
    api_key: str,
    username: str,
    report_id: str,
    task_type: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will export the final report, by consolidating all the
    information gathered, explored, predicted, and optimized.
    Side Effects:
    - Final report will be saved as a PDF file in the api_key's directory.
    """
    LOGGER.debug(f"Exporting for report {report_id}")
    json_data = {
        "api_key": api_key,
        "task_type": task_type,
        "inputs": inputs,
        "outputs": outputs
    }
    response = await make_request(DEFOG_BASE_URL + "/oracle/generate_report", json_data)
    mdx = response.get("mdx")
    if mdx is None:
        LOGGER.error("No MDX returned from backend.")
    else:
        LOGGER.debug(f"MDX generated for report {report_id}\n{mdx}")
    pdf = MarkdownPdf(toc_level=1)
    pdf.add_section(Section(mdx))
    report_file_path = get_report_file_path(api_key, report_id)
    pdf.meta["author"] = "Oracle"
    pdf.save(report_file_path)
    LOGGER.debug(f"Exported report {report_id} to {report_file_path}")
    return {"mdx": mdx, "report_file_path": report_file_path}


def get_report_file_path(api_key: str, report_id: str) -> str:
    """
    Helper function for getting the report file path based on the api_key and report_id.
    Reports are organized in the following directory structure:
    oracle/reports/{api_key}/report_{report_id}.pdf
    """
    report_dir = f"oracle/reports/{api_key}"
    if not os.path.exists(report_dir):
        os.makedirs(report_dir, exist_ok=True)
        LOGGER.debug(f"Created directory {report_dir}")
    report_file_path = f"{report_dir}/report_{report_id}.pdf"
    return report_file_path