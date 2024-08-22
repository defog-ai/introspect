import asyncio
import json
import os
import random
from asyncio import sleep
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List

from db_utils import OracleReports, OracleSources, engine
from generic_utils import make_request
from sqlalchemy import insert, update, select
from sqlalchemy.orm import Session

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

celery_async_executors = ThreadPoolExecutor(max_workers=4)


@celery_app.task
def begin_generation_task(
    api_key: str, username: str, report_id: int, task_type: str, inputs: Dict[str, Any]
):
    t_start = datetime.now()
    print(f"Starting celery task for {username} at {t_start}")
    with celery_async_executors:
        loop = asyncio.get_event_loop()
        task = loop.create_task(
            begin_generation_async_task(api_key, username, report_id, task_type, inputs)
        )
        loop.run_until_complete(task)
    t_end = datetime.now()
    time_elapsed = (t_end - t_start).total_seconds()
    print(f"Completed celery task for {username} in {time_elapsed:.2f} seconds.")


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
    while continue_generation:
        # call the control function with the current stage
        try:
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
            # check if the report is done
            if stage == "done":
                continue_generation = False
            else:
                # get the next stage
                stage = next_stage(stage, task_type)
        except Exception as e:
            # update the status of the report
            with Session(engine) as session:
                stmt = select(OracleReports).where(OracleReports.report_id == report_id)
                result = session.execute(stmt)
                report = result.scalar_one()
                report.status = "error"
                print(f"Error occurred in stage {stage}:\n{e}")
                session.commit()
            continue_generation = False


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
        print(f"Report {report_id} is done.")
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
    Side Effects:
    - Clarification questions generated at this stage will be saved to the
        `oracle_clarifications` table.
    """
    print(f"Gathering context for report {report_id}")
    question = inputs["question"]
    print("Got the following sources:")
    sources = []
    for source in inputs["sources"]:
        if "link" in source:
            source["type"] = "webpage"
            sources.append(source)
        print(f"{source}")
    json_data = {
        "api_key": api_key,
        "question": question,
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
            else:
                stmt = (
                    update(OracleSources)
                    .where(OracleSources.link == source["link"])
                    .values(source)
                )
                session.execute(stmt)
            print(f"Inserted source {source['link']} into the database.")
        session.commit()
    # TODO summarize all sources, attempt formulation and save clarification questions into DB
    return {"sources": sources_parsed}


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
    """
    # TODO implement this function
    # dummy print statement for now
    print(f"Exploring data for report {report_id}")


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
    print(f"Waiting for clarifications for report {report_id}")
    # sleep for a random amount of time to simulate work
    await sleep(random.random() * 2)
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
    print(f"Predicting for report {report_id}")
    # sleep for a random amount of time to simulate work
    await sleep(random.random() * 2)
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
    print(f"Optimizing for report {report_id}")
    # sleep for a random amount of time to simulate work
    await sleep(random.random() * 2)
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
    - Final report will be saved as a PDF file in the report_id's directory.
    """
    # TODO implement this function
    # dummy print statement for now
    print(f"Exporting for report {report_id}")
    # sleep for a random amount of time to simulate work
    await sleep(random.random() * 2)
    return {"export": "report exported"}
