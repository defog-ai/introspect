import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict

from generic_utils import make_request
from db_utils import (
    OracleReports,
    add_or_update_analysis,
    engine,
    get_report_data,
)
from oracle.celery_app import celery_app
from oracle.constants import TaskStage, TaskType, STAGE_TO_STATUS
from oracle.explore import explore_data
from oracle.export import generate_report
from oracle.gather_context import gather_context
from oracle.predict import predict
from oracle.optimize import optimize
from oracle.redis_utils import delete_analysis_task_id
from sqlalchemy import select
from sqlalchemy.orm import Session
from utils_logging import LOGGER, save_and_log, save_timing
import os


celery_async_executors = ThreadPoolExecutor(max_workers=4)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


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
    is_revision = "original_report_id" in inputs and inputs.get("is_revision")
    original_report_id = inputs.get("original_report_id", None)

    while continue_generation:
        # call the control function with the current stage
        try:
            LOGGER.info(f"Executing stage {stage} for report {report_id}")
            with Session(engine) as session:
                # update status of the report
                stmt = select(OracleReports).where(OracleReports.report_id == report_id)
                result = session.execute(stmt)
                report = result.scalar_one()
                # we want to add some sort of indicator to a revision report
                # just so we're able to filter it out on the front end (or elsewhere)
                report.status = (
                    "Revision: " + STAGE_TO_STATUS[stage]
                    if is_revision
                    else STAGE_TO_STATUS[stage]
                )

                # if this is is_revision, then also update the original_report_id with the same status but starting with "Revision in progress: "
                if is_revision:
                    stmt = select(OracleReports).where(
                        OracleReports.report_id == original_report_id
                    )
                    result = session.execute(stmt)
                    original_report = result.scalar_one()
                    original_report.status = (
                        "Revision in progress: " + STAGE_TO_STATUS[stage]
                    )

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
                report.status = (
                    "Revision: " + STAGE_TO_STATUS[stage]
                    if is_revision
                    else STAGE_TO_STATUS[stage]
                )
                report.outputs = outputs
                # same as above for the original report
                if is_revision:
                    stmt = select(OracleReports).where(
                        OracleReports.report_id == original_report_id
                    )
                    result = session.execute(stmt)
                    original_report = result.scalar_one()
                    original_report.status = (
                        "Revision in progress: " + STAGE_TO_STATUS[stage]
                    )

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
                # if this is is_revision, then just delete this report
                if is_revision:
                    session.delete(report)
                    # also update the original report back to "done"
                    stmt = select(OracleReports).where(
                        OracleReports.report_id == original_report_id
                    )
                    result = session.execute(stmt)
                    original_report = result.scalar_one()
                    original_report.status = "done"

                session.commit()
            continue_generation = False

        if stage == TaskStage.DONE:
            continue_generation = False
            # if this was an is_revision request, use the report_id passed in inputs (this is the freshly created revised report)
            # and update all the data of the original report from the newly created report (stored in inputs["original_report_id"])
            if "original_report_id" in inputs and inputs.get("is_revision"):
                original_report_id = inputs["original_report_id"]
                with Session(engine) as session:
                    # get the original report
                    stmt = select(OracleReports).where(
                        OracleReports.report_id == original_report_id
                    )
                    result = session.execute(stmt)
                    original_report = result.scalar_one()

                    # get the newly created report
                    stmt = select(OracleReports).where(
                        OracleReports.report_id == report_id
                    )
                    result = session.execute(stmt)
                    revised_report = result.scalar_one()

                    # Update all specified columns from revised report to original report
                    # Note: We don't copy 'inputs' since it contains revision metadata (is_revision, original_report_id, etc)
                    columns_to_update = [
                        "report_name",
                        "outputs",
                        "comments",
                        "feedback",
                    ]
                    for column in columns_to_update:
                        setattr(
                            original_report, column, getattr(revised_report, column)
                        )

                    # set report back to done
                    setattr(original_report, "status", "done")

                    # Delete the revised report since we've copied its data
                    session.delete(revised_report)
                    session.commit()
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
    return stage_result


@celery_app.task(name="generate_analysis_task")
def generate_analysis_task(
    api_key: str,
    report_id: str,
    analysis_id: str,
    new_analysis_question: str,
    recommendation_idx: int,
    previous_analyses: list,
):
    """Celery task for generating analysis asynchronously."""

    async def _run_analysis():
        try:
            # get report's data
            report_data = await get_report_data(report_id, api_key)
            if "error" in report_data:
                delete_analysis_task_id(analysis_id)
                return {"error": report_data["error"]}

            report_data = report_data["data"]

            # Call explore_data with a single analysis request
            inputs = {
                "user_question": new_analysis_question,
                "sources": report_data["inputs"].get("sources", []),
                "max_analyses": 1,
                "max_rounds": 1,
                "previous_analyses": previous_analyses,
            }

            # Reuse the outputs from the main report
            outputs = {
                "gather_context": report_data["outputs"].get("gather_context", {}),
                "explore": report_data["outputs"].get("explore", {}),
            }

            # Change the problem statement to the new analysis question
            outputs["gather_context"]["problem_statement"] = new_analysis_question

            result = await explore_data(
                api_key=api_key,
                report_id=report_id,
                task_type=TaskType.EXPLORATION,
                inputs=inputs,
                outputs=outputs,
                is_follow_on=True,
                follow_on_id=analysis_id,
            )

            if (
                "error" in result
                or "analyses" not in result
                or len(result["analyses"]) == 0
            ):
                # set status to error
                await add_or_update_analysis(
                    api_key=api_key,
                    analysis_id=analysis_id,
                    report_id=report_id,
                    status="ERROR",
                    analysis_json={
                        # reset the data to just be the question
                        "title": new_analysis_question,
                        "analysis_id": analysis_id,
                        # store this error and trace for debugging later
                        "error": str(e),
                        "trace": traceback.format_exc(),
                    },
                    mdx=None,
                )
                delete_analysis_task_id(analysis_id)
                return {"error": "Error generating analysis"}

            full_context_with_previous_analyses = result.get(
                "full_context_with_previous_analyses", []
            )

            analysis = result["analyses"][0]
            analysis["analysis_id"] = analysis_id

            # create an mdx for this analysis
            # just using the table that was generated
            LOGGER.info(analysis)

            # update the analysis json with the results so far
            await add_or_update_analysis(
                api_key=api_key,
                analysis_id=analysis_id,
                report_id=report_id,
                status="Understanding explored data to generate analysis",
                analysis_json=analysis,
                mdx=None,
            )

            # generate mdx for this analysis
            res = await make_request(
                DEFOG_BASE_URL + "/oracle/generate_analysis_mdx",
                {
                    "api_key": api_key,
                    "problem_statement": new_analysis_question,
                    "task_type": TaskType.EXPLORATION.value,
                    "analysis": analysis,
                    "context": full_context_with_previous_analyses,
                    "skip_rephrase": True,
                    "table_last": True,
                },
            )

            mdx = res["mdx"]
            if not mdx:
                delete_analysis_task_id(analysis_id)
                return {"error": "Error generating analysis mdx"}

            # add this analysis to the database
            await add_or_update_analysis(
                api_key=api_key,
                analysis_id=analysis["analysis_id"],
                report_id=report_id,
                status="DONE",
                analysis_json=analysis,
                mdx=mdx,
            )

            # Analysis is complete, remove the Redis key
            delete_analysis_task_id(analysis_id)
        except Exception as e:
            LOGGER.error(f"Error in generate_analysis_task: {str(e)}")
            await add_or_update_analysis(
                api_key=api_key,
                analysis_id=analysis_id,
                report_id=report_id,
                status="ERROR",
                analysis_json={
                    # reset the data to just be the question
                    "title": new_analysis_question,
                    "analysis_id": analysis_id,
                    # store this error and trace for debugging later
                    "error": str(e),
                    "trace": traceback.format_exc(),
                },
                mdx=None,
            )
            delete_analysis_task_id(analysis_id)

    return asyncio.run(_run_analysis())
