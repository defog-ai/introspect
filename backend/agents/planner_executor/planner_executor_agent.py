# the executor converts the user's task to steps and maps those steps to tools.
# also runs those steps
from copy import deepcopy
import traceback
from uuid import uuid4

from colorama import Fore, Style

from agents.planner_executor.execute_tool import execute_tool
from agents.clarifier.clarifier_agent import turn_into_statements
from tool_code_utilities import fetch_query_into_df
from db_utils import (
    get_analysis_data,
    get_assignment_understanding,
    update_analysis_data,
    update_assignment_understanding,
)
from utils import deduplicate_columns, warn_str, YieldList, add_indent
from .tool_helpers.toolbox_manager import get_tool_library_prompt
from .tool_helpers.tool_param_types import ListWithDefault
import asyncio
import requests

import yaml
import re
import pandas as pd
import os

import logging

logging.basicConfig(level=logging.INFO)


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
    logging.info(add_indent(indent_level) + " " + str(msg))


def error(msg):
    global indent_level
    logging.error(add_indent(indent_level) + " " + str(msg))


def warn(msg):
    global indent_level
    logging.warn(add_indent(indent_level) + " " + str(msg))


# store the outputs of multiple analysis in a global variable
# we keep this around for a while, in case we need to re-run a step v soon after it was run
# but we will clear this cache after a while
# things stored here, also specific to each step.
# {
#   "analysis_id_1": {
#     "user_question": user_question,
#     "dfg_api_key": dfg_api_key,
#     "toolboxes": toolboxes,
#     "assignment_understanding": assignment_understanding,
#     "dfg": None,
#     "llm_calls_url": llm_calls_url,
#     "analysis_assets_dir": analysis_assets_dir,
#     "dev": dev,
#     "temp": temp,
#     "output_1": ...
#     "output_2": ...
#   },
#   "analysis_id_2": {...}
#   "analysis_id_3": {...}
#   ...
# }
llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")
analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)

# check if analysis_assets_dir/datasets exists
if not os.path.exists(analysis_assets_dir + "/datasets"):
    os.makedirs(analysis_assets_dir + "/datasets")


class MissingDependencyException(Exception):
    def __init__(self, variable_name):
        # Call the base class constructor with the parameters it needs
        super().__init__(f"{variable_name}")

        # Now for your custom code...
        self.variable_name = variable_name


def get_input_value(inp, analysis_execution_cache):
    """
    Tries to figure out a value of an input.

    If the input starts with `global_dict.XXX`, and is not found in analysis_execution_cache, raises a MissingDependencyException.

    That exception is usually a signal to the calling function that it needs to run some parent step.
    """
    val = None

    if isinstance(inp, list):
        # this is an array
        val = []
        for inp in inp:
            val.append(get_input_value(inp, analysis_execution_cache))

    elif isinstance(inp, str) and inp.startswith("global_dict."):
        variable_name = inp.split(".")[1]
        # if analysis_execution_cache doesn't have this key, raise an error
        if variable_name not in analysis_execution_cache:
            # raise error
            raise MissingDependencyException(variable_name)
        else:
            # TODO: first look in the analysis_assets directory
            # asset_file_name = step_id + "_output" + "-" + input_name + ".feather"
            # find_asset(asset_file_name)
            # Then store in analysis_execution_cache
            val = analysis_execution_cache[variable_name]

    else:
        # simpler types
        if isinstance(inp, str):
            # if only numbers, return float
            if inp.isnumeric():
                val = float(inp)

            # if None as a string after stripping, return None
            if inp.strip() == "None":
                val = None
            val = inp

    return val


def resolve_step_inputs(inputs: dict, analysis_execution_cache: dict = {}):
    """
    Resolved the inputs to a step.
    This is mostly crucial for parsing analysis_execution_cache.XXX style of inputs, which occur if this step uses outputs from another step
    This works closely with the get_input_value function which is responsible for parsing a single input.
    An example step's yaml is:
    ```
    - description: Fetching 5 rows from the database to display.
        tool_name: data_fetcher_and_aggregator
        inputs:
        question: "Show me 5 rows from the database."
        outputs_storage_keys: ["five_rows"]
        done: true
    ```
    So the "inputs" is a dict with the key "question". Each input i to a tool is a key in that inputs object.

    That input i itself can be any python type.

    Iff that input i is a string and it starts with "analysis_execution_cache.", we will have extra logic:
    1. We will first try to find the output inside the analysis_assets folder. If we can't find it, we will call the parent step = the step that generated that `analysis_execution_cache.XXX` data. This will be one of the steps passed in `previous_responses` to the generate_single_step function.
    2. We will keep recursively calling the `run_tool` function till we resolve all the inputs.
    """

    resolved_inputs = {}

    for input_name, input_val in inputs.items():
        try:
            val = get_input_value(input_val, analysis_execution_cache)
            resolved_inputs[input_name] = val
        except MissingDependencyException as e:
            # let calling function handle this
            raise e
        except Exception as e:
            error(f"Error resolving input {input_name}: {input_val}")
            error(e)
            raise Exception(f"Error resolving input {input_name}: {input_val}")

    return resolved_inputs


def find_step_by_output_name(output_name, previous_steps):
    """
    Given an output name, find the step that generated this output.
    """
    for step in previous_steps:
        if output_name in step.get("outputs_storage_keys", []):
            return step
    return None


async def run_step(
    analysis_id,
    step,
    all_steps,
    analysis_execution_cache,
    skip_cache_storing=False,
    resolve_inputs=True,
    max_resolve_tries=4,
):
    """
    Runs a single step, updating the steps object *in place* with the results. Also re-runs all parent steps if required.

    General flow:
    1. If resolve_inputs is True, first try to resolve the inputs of this step. If it is False, we assume that the inputs are already resolved and go straight to step 4.
    2. If the inputs resolution gives a MissingDependencyException means that one of hte inputs is a global_dict.XXX type of input, which means we need to run a parent step. If any other error, fail.
    3. Run all the required parent steps recursively till the inputs are resolved.
    4. Now the inputs are resolved, run this step.
    5. Stores the run step in the respective analysis in the db
    """

    outputs_storage_keys = step["outputs_storage_keys"]

    info(f"Running step: {step['id']} with tool: {step['tool_name']}")
    add_indent_levels(1)

    # try to resolve the inputs to this step
    if resolve_inputs:

        # these retries are only triggered if we get a MissingDependencyException
        # I.e., if the LLM does not give us the right inputs to this step
        while max_resolve_tries > 0:
            # keep doing till we either resolve the inputs or raise an error while resolving
            # NOTE: we only decrease the above max_resolve_tries in case of exceptions
            try:
                # resolve the inputs
                resolved_inputs = resolve_step_inputs(
                    step["inputs"], analysis_execution_cache=analysis_execution_cache
                )
            except MissingDependencyException as e:
                missing_variable = e.variable_name
                info(f"Missing variable: {missing_variable}")
                # find the step that generated this variable
                # this should be one of the previous steps
                step_that_generated_this_output = find_step_by_output_name(
                    missing_variable, all_steps
                )
                if step_that_generated_this_output is None:
                    raise Exception(
                        f"Could not find the step that generated the output: {missing_variable}"
                    )
                else:
                    info(
                        f"Found step that generated the output: {missing_variable}. Putting that in run queue."
                    )

                    await run_step(
                        analysis_id=analysis_id,
                        step=step_that_generated_this_output,
                        all_steps=all_steps,
                        analysis_execution_cache=analysis_execution_cache,
                    )
            except Exception as e:
                error(f"Error while resolving step inputs: {e}")
                raise Exception(f"Error while resolving step inputs")
            finally:
                if max_resolve_tries == 0:
                    raise Exception(
                        f"Exceeded max tries while resolving the inputs to this step: {step['id']}"
                    )
                max_resolve_tries -= 1

        info(f"Resolved step inputs: {resolved_inputs}")
    else:
        resolved_inputs = step["inputs"]

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
            tool_function_inputs=resolved_inputs,
            global_dict=analysis_execution_cache,
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
            # 3. store the dataframe in the analysis_assets directory
            # 4. Finally store in the step object
            if data is not None and type(data) == type(pd.DataFrame()):
                db_path = step["id"] + "_output-" + output_name + ".feather"

                # deduplicate columns of this df
                deduplicated = deduplicate_columns(data)

                # store the dataframe in the analysis_execution_cache
                # name the df too
                if not skip_cache_storing:
                    analysis_execution_cache[output_name] = deduplicated
                    analysis_execution_cache[output_name].df_name = output_name

                # store the dataframe in the analysis_assets directory
                deduplicated.reset_index(drop=True).to_feather(
                    analysis_assets_dir + "/datasets/" + db_path
                )

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


def create_yaml_for_prompt_from_steps(steps=[]) -> list[str]:
    """
    Formats the steps array (as stored in the db)
    into yaml strings that can be used as a prompt for the LLM.

    We take selected properties from each step's dict
    convert it to a yaml string

    Then wrap each one in ```yaml...```

    Returns an array of strings
    """
    yaml_formatted_steps = []
    for step in steps:
        yaml_formatted_steps.append(
            yaml.dump(
                [
                    {
                        "description": step["description"],
                        "inputs": step["inputs"],
                        "outputs_storage_keys": step["outputs_storage_keys"],
                        "tool_name": step["tool_name"],
                        "done": step["done"],
                    }
                ],
                default_flow_style=False,
                sort_keys=False,
            )
        )

    return yaml_formatted_steps


def find_previous_steps_from_step_id(step_id, all_steps):
    """
    Finds *only* the previous steps of the provided step_id from an array of all steps
    If step is not found, it returns all the steps
    """
    # find the index of this step_id
    idx = len(all_steps)

    for i, step in enumerate(all_steps):
        if step["id"] == step_id:
            idx = i
            break

    return all_steps[:idx]


async def generate_assignment_understanding(
    analysis_id, clarification_questions, dfg_api_key
):
    """
    Generates the assignment understanding from the clarification questions.

    And stores in the defog_analyses table.
    """
    # get the assignment understanding aka answers to clarification questions
    assignment_understanding = None
    reset_indent_level()

    info(f"Clarification questions: {clarification_questions}")

    if len(clarification_questions) > 0:
        try:
            assignment_understanding = await turn_into_statements(
                clarification_questions, dfg_api_key
            )
        except Exception as e:
            warn(
                "Could not generate understanding. The answers might not be what the user wants. Resorting to blank string"
            )
            error(e)
            assignment_understanding = []

    info(f"Assignment understanding: {assignment_understanding}")

    err = update_assignment_understanding(
        analysis_id=analysis_id, understanding=assignment_understanding
    )

    return err, assignment_understanding


async def prepare_cache(
    analysis_id,
    dfg_api_key,
    user_question,
    toolboxes=[],
    dev=False,
    temp=False,
):
    reset_indent_level()
    analysis_execution_cache = {}
    analysis_execution_cache["dfg_api_key"] = dfg_api_key
    analysis_execution_cache["user_question"] = user_question
    analysis_execution_cache["toolboxes"] = toolboxes
    analysis_execution_cache["dev"] = dev
    analysis_execution_cache["temp"] = temp

    err, assignment_understanding = get_assignment_understanding(
        analysis_id=analysis_id
    )

    if err:
        warn("Could not fetch assignment understanding from the db. Using empty list")
        assignment_understanding = []

    analysis_execution_cache["assignment_understanding"] = assignment_understanding

    info("Created cache:")
    info(analysis_execution_cache)

    return analysis_execution_cache


async def generate_single_step(
    dfg_api_key,
    analysis_id,
    user_question,
    toolboxes=[],
    dev=False,
    temp=False,
    assignment_understanding="",
    # NOTE: we will remove this feature of "parent/nested/follow-on" analysis.
    # Keeping this here for now, but will remove it once we reach a stable point.
    # parent_analyses=[],
    # similar_plans=[],
    # direct_parent_analysis=None,
):
    """
    This function:
    1. Prepares all the data needed to generate a step: the global_dict, the tool_library_prompt, the assignment_understanding, etc.
       Also prepares the previous steps in the analysis as a yaml for the prompt.
    2. Calls defog-backend-python to generate the next step.
    3. Runs that step.
    4. Stores the result of the step.
    5. Returns the generated step + result.
    """
    reset_indent_level()

    unique_id = str(uuid4())

    # prepare the cache
    analysis_execution_cache = await prepare_cache(
        analysis_id,
        dfg_api_key,
        user_question,
        toolboxes,
        dev,
        temp,
    )

    # NOTE: see note above
    # err, user_question_context = await get_analysis_question_context(analysis_id)
    # if err:
    #     user_question_context = None

    tool_library_prompt = await get_tool_library_prompt(toolboxes, user_question)

    # make calls to the LLM to get the next step
    llm_server_url = os.environ.get("LLM_SERVER_ENDPOINT", None)

    # this will default to empty string, so make sure to set to None
    if not llm_server_url:
        llm_server_url = None
    info(f"LLM_SERVER_ENDPOINT set to: `{llm_server_url}`")

    err, analysis_data = get_analysis_data(analysis_id)
    if err:
        # can't do much about not being able to fetch data. fail.
        raise Exception(err)

    gen_steps_stage_output = analysis_data.get("gen_steps", {})

    if gen_steps_stage_output.get("success", False):
        # find the index of this
        all_steps = gen_steps_stage_output.get("steps", [])
    else:
        all_steps = []

    previous_steps = find_previous_steps_from_step_id(unique_id, all_steps)

    # format the above steps into yaml strings for the prompt
    previous_responses_yaml_for_prompt = create_yaml_for_prompt_from_steps(
        previous_steps
    )

    # TODO: construct using previous steps' outputs
    next_step_data_description = ""

    info(f"Previous responses: {previous_responses_yaml_for_prompt}")

    payload = {
        "request_type": "create_plan",
        "question": user_question,
        "tool_library_prompt": tool_library_prompt,
        "assignment_understanding": analysis_execution_cache[
            "assignment_understanding"
        ],
        "previous_responses": previous_responses_yaml_for_prompt,
        "next_step_data_description": next_step_data_description,
        "api_key": dfg_api_key,
        "plan_id": analysis_id,
        "llm_server_url": llm_server_url,
        "model_name": os.environ.get("LLM_MODEL_NAME", None),
        "dev": dev,
        "temp": temp,
        "parent_questions": [],
        "assignment_understanding": assignment_understanding,
        # NOTE: disabled for now. See note above.
        # "parent_questions": [p["user_question"] for p in parent_analyses],
        # "similar_plans": similar_plans[:2],
    }

    res = (
        await asyncio.to_thread(
            requests.post, llm_calls_url, json=payload, verify=False
        )
    ).json()
    step_yaml = res["generated_step"]
    info("Generated step yaml:")
    info(step_yaml)

    step_yaml = re.search("(?:```yaml)([\s\S]*?)(?=```)", step_yaml)

    if step_yaml is None:
        error(
            f"Seems like no step was generated. This was the response from the LLM: \n {step_yaml}"
        )
        raise Exception("Invalid response from the model")

    step = yaml.safe_load(step_yaml[1].strip())[0]
    # give a unique id to this step
    step["id"] = unique_id

    await run_step(
        analysis_id=analysis_id,
        step=step,
        all_steps=all_steps,
        analysis_execution_cache=analysis_execution_cache,
        # just for testing for now
        skip_cache_storing=True,
    )

    return step


def find_dependent_steps(step, all_steps):
    """
    Given a step, find all the steps that depend on this step.
    """
    dependent_steps = []

    # output keys of the step we want to find the dependents of
    output_keys = step.get("outputs_storage_keys", [])

    if len(output_keys) > 0:
        for s in all_steps:
            # skip if it's the same step
            if step["id"] == s["id"]:
                continue
            inputs = s.get("inputs", {}).values()
            # if any of the inputs to this step start with global_dict.[output_key], then this step is dependent on the step we're looking at
            for inp in inputs:
                if isinstance(inp, str) and inp.startswith("global_dict."):
                    variable_name = inp.split(".")[1]
                    if variable_name in output_keys:
                        dependent_steps.append(s)
                        # also find the dependents of this step
                        dependent_steps.extend(find_dependent_steps(s, all_steps))

    return dependent_steps


async def rerun_step(
    step,
    all_steps,
    dfg_api_key,
    analysis_id,
    user_question,
    toolboxes=[],
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
        toolboxes,
        dev,
        temp,
    )

    await run_step(
        analysis_id=analysis_id,
        step=step,
        all_steps=all_steps,
        analysis_execution_cache=analysis_execution_cache,
    )

    dependent_steps = find_dependent_steps(step, all_steps)

    logging.info(
        f"{len(dependent_steps)} dependent steps found: {[[x['id'], x['tool_name']]for x in dependent_steps]}"
    )

    for dependent_step in dependent_steps:
        await run_step(
            analysis_id=analysis_id,
            step=dependent_step,
            all_steps=all_steps,
            analysis_execution_cache=analysis_execution_cache,
        )

    # now after we've rerun everything, get the latest analysis data from the db and return those steps
    err, analysis_data = get_analysis_data(analysis_id)
    if err:
        # can't do much about not being able to fetch data. fail.
        raise Exception(err)

    new_steps = analysis_data.get("gen_steps", {}).get("steps", [])

    return new_steps
