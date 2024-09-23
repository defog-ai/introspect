import asyncio
import json
import os
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List

import pdfkit
from celery.utils.log import get_task_logger
from db_utils import (
    OracleReports,
    OracleSources,
    engine,
    update_imported_tables,
    update_imported_tables_db,
)
from generic_utils import make_request
from markdown2 import Markdown
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from utils_logging import LOG_LEVEL, save_and_log, save_timing
from oracle.celery_app import celery_app
from oracle.explore import explore_data

EXPLORATION = "exploration"
PREDICTION = "prediction"
OPTIMIZATION = "optimization"
TASK_TYPES = [
    EXPLORATION,
    PREDICTION,
    OPTIMIZATION,
]
DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
PARSED_SCHEMA = "parsed" # schema name to store parsed tables
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
            with Session(engine) as session:
                # update status of the report
                stmt = select(OracleReports).where(OracleReports.report_id == report_id)
                result = session.execute(stmt)
                report = result.scalar_one()
                report.status = stage
                session.commit()
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
        if source.startswith("http"):
            source["type"] = "webpage"
        elif source.endswith(".pdf"):
            source["type"] = "pdf"
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

    parse_table_tasks = []
    table_keys = []
    for source in sources_parsed:
        for i, table in enumerate(source.get("tables", [])):
            column_names = table.get("column_names")
            rows = table.get("rows")
            if not column_names or not rows:
                LOGGER.error(
                    f"No column names or rows found in table {i}. Skipping table:\n{table}"
                )
                continue
            table_data = {
                "api_key": api_key,
                "all_rows": [table["column_names"]] + table["rows"],
                "previous_text": table.get("previous_text"),
            }
            if table.get("table_page", None):
                table_keys.append((source["link"], table["table_page"])) # use table page as index if available
            else:
                table_keys.append((source["link"], i))
            parse_table_tasks.append(
                make_request(
                    DEFOG_BASE_URL + "/unstructured_data/infer_table_properties",
                    table_data,
                )
            )
    parsed_tables = await asyncio.gather(*parse_table_tasks)
    inserted_tables = {}
    with engine.connect() as connection:
        for (link, table_index), parsed_table in zip(table_keys, parsed_tables):
            try:
                # input validation
                if "table_name" not in parsed_table:
                    LOGGER.error("No table name found in parsed table.")
                    continue
                table_name = parsed_table["table_name"]
                table_description = parsed_table.get("table_description", None)
                if "columns" not in parsed_table:
                    LOGGER.error(f"No columns found in parsed table `{table_name}`.")
                    continue
                columns = parsed_table["columns"]
                column_names = [column["column_name"] for column in columns]
                num_cols = len(columns)
                if "rows" not in parsed_table:
                    LOGGER.error(f"No rows found in parsed table `{table_name}`.")
                    continue
                rows = parsed_table[
                    "rows"
                ]  # 2D list of data TODO: fix parsing of rows in self-hosted: infer_table_properties. currently splits on commas even if comma is within the same sentence or there's comma in value e.g. $10,000
                data = [column_names] + rows
                # check data has correct number of columns passed for each row
                if not all(len(row) == len(data[0]) for row in data):
                    LOGGER.error(
                        f"Unable to insert table `{table_name}.` Data has mismatched number of columns for each row. Header has {len(data[0])} columns: {data[0]}, but data has {len(data[1])} columns: {data[1]}."
                    )
                    continue

                schema_table_name = f"{PARSED_SCHEMA}.{table_name}"
                # create the table and insert the data into imported_tables database, parsed schema
                update_imported_tables_db(link, table_index, table_name, data, PARSED_SCHEMA)
                # update the imported_tables table in internal db
                update_imported_tables(
                    link, table_index, schema_table_name, table_description
                )    
                [column.pop("fn", None) for column in columns] # remove "fn" key if present before updating metadata
                inserted_tables[schema_table_name] = columns
            except Exception as e:
                LOGGER.error(
                    f"Error occurred in parsing table: {e}\n{traceback.format_exc()}"
                )
    ts = save_timing(ts, "Tables saved", timings)
    # get and update metadata if inserted_tables is not empty
    if inserted_tables:
        response = await make_request(
            DEFOG_BASE_URL + "/get_metadata", {"api_key": api_key, "imported": True}
        )
        md = response.get("table_metadata", {}) if response else {}
        md.update(inserted_tables)
        response = await make_request(
            DEFOG_BASE_URL + "/update_metadata",
            {"api_key": api_key, "table_metadata": md, "imported": True},
        )
        LOGGER.info(f"Updated metadata for api_key {api_key}")
        ts = save_timing(ts, "Metadata updated", timings)
    else:
        LOGGER.error("No parsed tables to save.")

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
        LOGGER.error(
            f"Error occurred in combining summaries: {combined_summary['error']}"
        )
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
        "outputs": outputs,
    }
    response = await make_request(DEFOG_BASE_URL + "/oracle/generate_report", json_data)
    mdx = response.get("mdx")
    if mdx is None:
        LOGGER.error("No MDX returned from backend.")
    else:
        LOGGER.debug(f"MDX generated for report {report_id}\n{mdx}")
    markdowner = Markdown(extras=["tables"])
    html_string = markdowner.convert(mdx)
    report_file_path = get_report_file_path(api_key, report_id)
    pdfkit.from_string(
        html_string, report_file_path, options={"enable-local-file-access": ""}
    )
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
