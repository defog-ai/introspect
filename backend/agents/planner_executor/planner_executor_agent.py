# the executor converts the user's task to steps and maps those steps to tools.
# also runs those steps
from copy import deepcopy
import traceback

from agents.planner_executor.execute_tool import execute_tool
from agents.clarifier.clarifier_agent import turn_into_statements
from tool_code_utilities import fetch_query_into_df
from db_analysis_utils import (
    get_analysis_data,
    get_assignment_understanding,
    update_analysis_data,
    update_assignment_understanding,
)
from utils import deduplicate_columns, add_indent

import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=SyntaxWarning)

import logging

LOGGER = logging.getLogger("server")


# some helper functions for prettier logging

indent_level = 0


def add_indent_levels(level=1):
    global indent_level
    indent_level += level


def set_indent_level(level=0):
    global indent_level
    indent_level = level


def reset_indent_level():
    global indent_level
    indent_level = 0


def info(msg):
    global indent_level
    LOGGER.info(add_indent(indent_level) + " " + str(msg))


def error(msg):
    global indent_level
    LOGGER.error(add_indent(indent_level) + " " + str(msg))


def warn(msg):
    global indent_level
    LOGGER.warn(add_indent(indent_level) + " " + str(msg))


async def run_step(
    analysis_id,
    step,
    analysis_execution_cache,
    skip_cache_storing=False,
):
    """
    Runs a single step, updating the steps object *in place* with the results. Also re-runs all parent steps if required.

    General flow:
    1. Now the inputs are resolved, run this step.
    2. Stores the run step in the respective analysis in the db
    """

    outputs_storage_keys = step["outputs_storage_keys"]
    info(f"Running step: {step['id']} with tool: {step['tool_name']}")
    add_indent_levels(1)

    inputs = step["inputs"]

    # once we have the resolved inputs, run the step
    # but if this is data fetcher and aggregator, we need to check what changed in the inputs
    # if the question changed, then run the tool itself, where we send a req to defog and get the sql
    # if the question is the same, but the sql changed, then just run the sql again
    results = None
    executed = False
    tool_input_metadata = step.get("input_metadata", {})

    # for us to check anything, we need to ensure this isn't the first time this step is running
    # check if model_generated_inputs and inputs even exist
    if "model_generated_inputs" in step and "inputs" in step:
        if step["tool_name"] == "data_fetcher_and_aggregator":
            model_generated_question = step["model_generated_inputs"]["question"]
            current_question = step["inputs"]["question"]

            # if the question has not changed, we will make executed to True, then run the sql
            if model_generated_question == current_question:
                info("Question has not changed. Re-running only the sql.")
                executed = True
                try:
                    output_df, final_sql_query = await fetch_query_into_df(
                        api_key=analysis_execution_cache["dfg_api_key"],
                        sql_query=step["sql"],
                        temp=analysis_execution_cache["temp"],
                    )
                    results = {
                        "sql": final_sql_query,
                        "outputs": [
                            {
                                "data": output_df,
                            }
                        ],
                    }
                    analysis_execution_cache[outputs_storage_keys[0]] = output_df
                except Exception as e:
                    traceback.print_exc()
                    results = {
                        "error_message": "Could not run the sql query. Is it correct?"
                    }
            else:
                info(
                    "Question has changed. Re-running the tool to fetch the sql for the new question."
                )

    # if we didn't execute yet, do it now by running the tool
    if not executed:
        results, tool_input_metadata = await execute_tool(
            function_name=step["tool_name"],
            tool_function_inputs=inputs,
        )

    step["error_message"] = results.get("error_message")

    step["input_metadata"] = tool_input_metadata

    step["model_generated_inputs"] = deepcopy(step["inputs"])

    # merge result into the step object
    step.update(results)

    # but not outputs
    # we will construct the outputs object below
    step["outputs"] = {}

    # if there's no error, check if zip is possible
    if not results.get("error_message"):
        # if number of outputs does not match the number of keys to store the outputs in
        # raise exception
        # this should never really happen
        output_storage_keys = step.get("outputs_storage_keys", [])
        outputs = results.get("outputs", [])
        if len(output_storage_keys) != len(outputs):
            warn(
                f"Length of outputs_storage_keys and outputs don't match. Outputs: {results.get('outputs')}. Force matching with index suffixes."
            )
            # if outputs_storage_keys <= outputs, append the difference with output_idx
            if len(output_storage_keys) <= len(outputs):
                for i in range(len(output_storage_keys), len(outputs)):
                    step["outputs_storage_keys"].append(
                        f"{step['tool_name']}_output_{i}"
                    )
            else:
                step["outputs_storage_keys"] = step["outputs_storage_keys"][
                    : len(outputs)
                ]

        # zip and store the output keys to analysis_execution_cache
        for output_name, output_value in zip(
            step["outputs_storage_keys"], results.get("outputs")
        ):
            data = output_value.get("data")
            reactive_vars = output_value.get("reactive_vars")
            chart_images = output_value.get("chart_images")

            step["outputs"][output_name] = {}

            info("Parsing output: " + output_name)

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

            if reactive_vars is not None:
                step["outputs"][output_name]["reactive_vars"] = reactive_vars

            if chart_images is not None:
                step["outputs"][output_name]["chart_images"] = chart_images

            info(f"Stored output: {output_name}")

    # update the analysis data in the db
    if analysis_id:
        await update_analysis_data(
            analysis_id=analysis_id,
            request_type="gen_steps",
            new_data=[step],
            # if this is a new step, this will simply append
            # but if we're running an existing step, this will overwrite it with the new one
            overwrite_key="id",
        )


async def generate_assignment_understanding(
    analysis_id, clarification_questions, dfg_api_key
):
    """
    Generates the assignment understanding from the clarification questions.

    And stores in the defog_analyses table.
    """
    # get the assignment understanding aka answers to clarification questions
    err = None
    assignment_understanding = None
    reset_indent_level()

    info(f"Clarification questions: {clarification_questions}")

    if len(clarification_questions) > 0:
        try:
            assignment_understanding = await turn_into_statements(
                clarification_questions, dfg_api_key
            )
            err = await update_assignment_understanding(
                analysis_id=analysis_id, understanding=assignment_understanding
            )
        except Exception as e:
            error(e)
            assignment_understanding = None

    info(f"Assignment understanding: {assignment_understanding}")

    return err, assignment_understanding


async def prepare_cache(
    analysis_id,
    dfg_api_key,
    user_question,
    dev=False,
    temp=False,
):
    reset_indent_level()
    analysis_execution_cache = {}
    analysis_execution_cache["dfg_api_key"] = dfg_api_key
    analysis_execution_cache["user_question"] = user_question
    analysis_execution_cache["dev"] = dev
    analysis_execution_cache["temp"] = temp

    err, assignment_understanding = await get_assignment_understanding(
        analysis_id=analysis_id
    )

    if err:
        warn("Could not fetch assignment understanding from the db. Using empty list")
        assignment_understanding = []

    analysis_execution_cache["assignment_understanding"] = assignment_understanding

    info("Created cache:")
    info(analysis_execution_cache)

    return analysis_execution_cache


async def rerun_step(
    step,
    all_steps,
    dfg_api_key,
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
        dfg_api_key,
        user_question,
        dev,
        temp,
    )

    await run_step(
        analysis_id=analysis_id,
        step=step,
        all_steps=all_steps,
        analysis_execution_cache=analysis_execution_cache,
    )

    # now after we've rerun everything, get the latest analysis data from the db and return those steps
    err, analysis_data = await get_analysis_data(analysis_id)
    if err:
        # can't do much about not being able to fetch data. fail.
        raise Exception(err)

    new_steps = analysis_data.get("gen_steps", {}).get("steps", [])

    return new_steps
