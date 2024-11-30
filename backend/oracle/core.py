import asyncio
import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict

import pdfkit
from db_utils import OracleReports, engine
from generic_utils import make_request
from markdown2 import Markdown
from oracle.celery_app import celery_app, LOGGER
from oracle.constants import TaskStage, TaskType, DEFOG_BASE_URL, STAGE_TO_STATUS
from oracle.explore import explore_data
from oracle.gather_context import gather_context
from oracle.predict import predict
from oracle.optimize import optimize
from sqlalchemy import select
from sqlalchemy.orm import Session
from utils_logging import save_and_log, save_timing, truncate_obj


celery_async_executors = ThreadPoolExecutor(max_workers=4)


@celery_app.task
def begin_generation_task(
    api_key: str,
    report_id: int,
    task_type_str: str,
    inputs: Dict[str, Any],
):
    """
    Synchronous wrapper for the asynchronous task.
    This is the entrypoint for the celery app, and requires input types to be
    serializable, as it will be serialized and deserialized when passed to the
    celery worker.
    """
    t_start = datetime.now()
    try:
        task_type = TaskType(task_type_str)
    except ValueError:
        raise ValueError(f"Invalid task_type_str: {task_type_str}")
    LOGGER.info(f"Starting celery task for {api_key} at {t_start}")
    with celery_async_executors:
        loop = asyncio.get_event_loop()
        task = loop.create_task(
            begin_generation_async_task(api_key, report_id, task_type, inputs)
        )
        loop.run_until_complete(task)
    t_end = datetime.now()
    time_elapsed = (t_end - t_start).total_seconds()
    LOGGER.info(f"Completed celery task for {api_key} in {time_elapsed:.2f} seconds.")


async def begin_generation_async_task(
    api_key: str,
    report_id: int,
    task_type: TaskType,
    inputs: Dict[str, Any],
):
    """
    This is the entry point for the oracle, which will kick off the control flow,
    by starting the first stage of the report generation process.
    This function call is long-running, and will not return immediately.
    It will await on the next stage to be completed before proceeding to the next stage.
    It will only return when the report is done, or an error has occurred.

    Every call to control is scoped over a single report_id, which can only
    belong to 1 api_key.
    """
    stage = TaskStage.GATHER_CONTEXT
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
                report.status = STAGE_TO_STATUS[stage]
                session.commit()
            stage_result = await execute_stage(
                api_key=api_key,
                report_id=report_id,
                task_type=task_type,
                stage=stage,
                inputs=inputs,
                outputs=outputs,
            )
            outputs[stage.value] = stage_result
            # update the status and current outputs of the report generation
            with Session(engine) as session:
                stmt = select(OracleReports).where(OracleReports.report_id == report_id)
                result = session.execute(stmt)
                report = result.scalar_one()
                report.status = STAGE_TO_STATUS[stage]
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
                outputs[stage.value] = {"error": str(e) + "\n" + traceback.format_exc()}
                report.outputs = outputs
                report.status = "error"
                session.commit()
            continue_generation = False

        if stage == TaskStage.DONE:
            continue_generation = False
        # perform logging for current stage
        if continue_generation:
            ts = save_timing(ts, f"Stage {stage} completed", timings)
            stage = next_stage(stage, task_type)
        else:
            save_and_log(ts, f"Report {report_id} completed", timings)


def next_stage(stage: TaskStage, task_type: TaskType) -> TaskStage:
    if stage == TaskStage.GATHER_CONTEXT:
        return TaskStage.EXPLORE
    elif stage == TaskStage.EXPLORE:
        if task_type == TaskType.EXPLORATION:
            return TaskStage.EXPORT
        elif task_type == TaskType.PREDICTION:
            return TaskStage.PREDICT
        elif task_type == TaskType.OPTIMIZATION:
            return TaskStage.OPTIMIZE
    elif stage == TaskStage.PREDICT:
        return TaskStage.EXPORT
    elif stage == TaskStage.OPTIMIZE:
        return TaskStage.EXPORT
    elif stage == TaskStage.EXPORT:
        return TaskStage.DONE
    else:
        raise ValueError(f"Stage {stage} not recognized.")


async def execute_stage(
    api_key: str,
    report_id: str,
    task_type: TaskType,
    stage: TaskStage,
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
    if stage == TaskStage.GATHER_CONTEXT:
        stage_result = await gather_context(
            api_key=api_key,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == TaskStage.EXPLORE:
        stage_result = await explore_data(
            api_key=api_key,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == TaskStage.PREDICT:
        stage_result = await predict(
            api_key=api_key,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == TaskStage.OPTIMIZE:
        stage_result = await optimize(
            api_key=api_key,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == TaskStage.EXPORT:
        stage_result = await generate_report(
            api_key=api_key,
            report_id=report_id,
            task_type=task_type,
            inputs=inputs,
            outputs=outputs,
        )
    elif stage == TaskStage.DONE:
        stage_result = None
    # add more stages here for new report sections if necessary in the future
    else:
        raise ValueError(f"Stage {stage} not recognized.")
    return stage_result


async def generate_report(
    api_key: str,
    report_id: str,
    task_type: TaskType,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will generate the final report, by consolidating all the
    information gathered, explored, predicted, and optimized.
    """
    LOGGER.info(f"Exporting for report {report_id}")
    LOGGER.debug(f"inputs: {inputs}")
    LOGGER.debug(f"inputs: {outputs}")
    json_data = {
        "api_key": api_key,
        "task_type": task_type.value,
        "inputs": inputs,
        "outputs": outputs,
    }

    # generate the initial markdown
    response = await make_request(
        DEFOG_BASE_URL + "/oracle/generate_report", json_data, timeout=300
    )

    md = response.get("md")
    mdx = response.get("mdx")
    if md is None:
        LOGGER.error("No MD returned from backend.")
    else:
        # log truncated markdown for debugging
        trunc_md = truncate_obj(md, max_len_str=1000, to_str=True)
        LOGGER.debug(f"MD generated for report {report_id}\n{trunc_md}")

    # generate a synthesized introduction to the report
    introduction_md = await make_request(
        DEFOG_BASE_URL + "/oracle/synthesize_report",
        {"md": md, "api_key": api_key},
        timeout=300,
    )

    intro_md = introduction_md.get("md")
    if intro_md is None:
        LOGGER.error("No introduction MD returned from backend.")
    else:
        trunc_intro_md = truncate_obj(intro_md, max_len_str=1000, to_str=True)
        LOGGER.debug(
            f"Introduction MD generated for report {report_id}\n{trunc_intro_md}"
        )

    return {
        "md": "# Executive Summary\n\n" + intro_md + "\n\n" + md,
        "mdx": "# Executive Summary\n\n" + intro_md + "\n\n" + mdx,
    }


def get_report_image_path(api_key: str, report_id: str, image_file_name: str) -> str:
    """
    Helper function for getting the report image path based on the api_key, report_id and image file name.
    """
    return f"oracle/reports/{api_key}/report_{report_id}/{image_file_name}"


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
