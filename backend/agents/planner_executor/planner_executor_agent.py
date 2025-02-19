# the executor converts the user's task to steps and maps those steps to tools.
# also runs those steps
from agents.planner_executor.tools.all_tools import tools
from agents.planner_executor.tools.data_fetching import data_fetcher_and_aggregator
from utils_clarification import turn_clarifications_into_statement
from tool_code_utilities import fetch_query_into_df
from db_analysis_utils import (
    get_analysis,
    get_assignment_understanding,
    update_analysis_data,
    update_assignment_understanding,
)
from utils import deduplicate_columns
from utils_logging import LOGGER

import pandas as pd
import warnings

warnings.simplefilter(action="ignore", category=SyntaxWarning)


async def run_step(
    analysis_id, step, analysis_execution_cache, db_name, skip_cache_storing=False
):
    """
    Runs a single step, updating the steps object in place with the results.

    Args:
        analysis_id: ID of the analysis
        step: Step object containing tool and input information
        analysis_execution_cache: Cache for storing analysis results
        skip_cache_storing: Whether to skip storing results in cache
    """
    LOGGER.info(f"Running step {step['id']} with tool: {step['tool_name']}")

    async def handle_data_fetcher():
        """Handle data fetcher and aggregator specific logic"""
        if not ("model_generated_inputs" in step and "inputs" in step):
            return None, False

        if step["tool_name"] != "data_fetcher_and_aggregator":
            return None, False

        model_generated_question = step["model_generated_inputs"]["question"]
        current_question = step["inputs"]["question"]

        if model_generated_question != current_question:
            LOGGER.info("Question has changed. Re-running tool to fetch new SQL.")
            return None, False

        LOGGER.info("Question unchanged. Re-running SQL only.")
        try:
            output_df, final_sql_query = await fetch_query_into_df(
                db_name=analysis_execution_cache["db_name"],
                sql_query=step["sql"],
                question=current_question,
            )
            results = {"sql": final_sql_query, "outputs": [{"data": output_df}]}
            analysis_execution_cache[step["outputs_storage_keys"][0]] = output_df
            return results, True
        except Exception as e:
            LOGGER.error(f"SQL execution failed: {str(e)}")
            return {
                "error_message": "Could not run the SQL query. Is it correct?"
            }, True

    def align_output_keys(output_storage_keys, outputs):
        """Align output storage keys with outputs"""
        if len(output_storage_keys) == len(outputs):
            return output_storage_keys

        LOGGER.warning(
            f"Mismatched outputs_storage_keys and outputs length. Adjusting..."
        )
        if len(output_storage_keys) <= len(outputs):
            return output_storage_keys + [
                f"{step['tool_name']}_output_{i}"
                for i in range(len(output_storage_keys), len(outputs))
            ]
        return output_storage_keys[: len(outputs)]

    # Try data fetcher specific handling first
    results, executed = await handle_data_fetcher()

    # If not handled by data fetcher, execute the tool
    if not executed:
        results = await data_fetcher_and_aggregator(
            question=step["inputs"]["question"],
            db_name=db_name,
            hard_filters=step["inputs"]["hard_filters"],
            previous_context=step["inputs"]["previous_context"],
        )

        step["input_metadata"] = tools["data_fetcher_and_aggregator"]["input_metadata"]

    # Update step with results
    step["error_message"] = results.get("error_message")
    step["model_generated_inputs"] = step["inputs"].copy()
    step.update(results)
    step["outputs"] = {}

    # Process outputs if no errors
    if not results.get("error_message"):
        outputs = results.get("outputs", [])
        step["outputs_storage_keys"] = align_output_keys(
            step.get("outputs_storage_keys", []), outputs
        )

        # Process each output
        for output_name, output_value in zip(step["outputs_storage_keys"], outputs):
            LOGGER.info(f"Processing output: {output_name}")
            step["outputs"][output_name] = {}

            # Extract data from output_value
            data = output_value.get("data")

            # if the output has data and it is a pandas dataframe,
            # 1. deduplicate the columns
            # 2. store the dataframe in the analysis_execution_cache
            # 3. Finally store in the step object
            if data is not None and type(data) == type(pd.DataFrame()):
                # deduplicate columns of this df
                deduplicated = deduplicate_columns(data)

                # store the dataframe in the analysis_execution_cache
                # name the df too
                if not skip_cache_storing:
                    analysis_execution_cache[output_name] = deduplicated
                    analysis_execution_cache[output_name].df_name = output_name

                step["outputs"][output_name]["data"] = deduplicated.to_csv(
                    float_format="%.3f", index=False
                )

            LOGGER.info(f"Stored output: {output_name}")

    # update the analysis data in the db
    # await update_analysis_data(
    #     analysis_id=analysis_id,
    #     new_data=[step],
    # )


async def generate_assignment_understanding(
    analysis_id, clarification_questions, db_name
):
    """
    Generates the assignment understanding from the clarification questions.

    And stores in the analyses table.
    """
    # get the assignment understanding aka answers to clarification questions
    assignment_understanding = None

    LOGGER.info(f"Clarification questions: {clarification_questions}")

    if len(clarification_questions) > 0:
        try:
            assignment_understanding = await turn_clarifications_into_statement(
                clarification_questions, db_name
            )
        except Exception as e:
            LOGGER.error(e)
            assignment_understanding = None

    LOGGER.info(f"Assignment understanding: {assignment_understanding}")

    return assignment_understanding


async def prepare_cache(
    analysis_id,
    db_name,
    user_question,
    dev=False,
    temp=False,
):
    analysis_execution_cache = {}
    analysis_execution_cache["db_name"] = db_name
    analysis_execution_cache["user_question"] = user_question
    analysis_execution_cache["dev"] = dev
    analysis_execution_cache["temp"] = temp

    err, assignment_understanding = await get_assignment_understanding(
        analysis_id=analysis_id
    )

    if err:
        LOGGER.warning(
            "Could not fetch assignment understanding from the db. Using empty list"
        )
        assignment_understanding = []

    analysis_execution_cache["assignment_understanding"] = assignment_understanding

    LOGGER.info("Created cache:")
    LOGGER.info(analysis_execution_cache)

    return analysis_execution_cache


async def rerun_step(
    step,
    all_steps,
    db_name,
    analysis_id,
    user_question,
    dev=False,
    temp=False,
):
    """
    TODO: use stored tool code from the client instead of using saved tool code in db.
    Run a step again, running both the parents AND dependents of this step.

    Here all_steps and step is coming from the front end/client, NOT from the db. This is because we assume a person clicks on rerun_step when they have edited the inputs of a step and want to re-run it. And we don't store-on-edit the inputs to the db anymore. The edited versions only live on the front end.

    1. First simply call run_step on this step. That will take care of running the parents.
    2. Find the dependents of this step, in increasing order of depth in the DAG.
    3. Run each of those steps.
    4. Returns all steps with modified data.
    """

    # prepare the cache
    analysis_execution_cache = await prepare_cache(
        analysis_id,
        db_name,
        user_question,
        dev,
        temp,
    )

    await run_step(
        analysis_id=analysis_id,
        step=step,
        analysis_execution_cache=analysis_execution_cache,
        db_name=db_name,
    )

    # now after we've rerun everything, get the latest analysis data from the db and return those steps
    err, analysis_data = await get_analysis(analysis_id)
    if err:
        # can't do much about not being able to fetch data. fail.
        raise Exception(err)

    new_steps = analysis_data.get("gen_steps", {}).get("steps", [])

    return new_steps
