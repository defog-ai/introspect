import inspect
from agents.planner_executor.tool_helpers.all_tools import *
from db_utils import store_tool_run, get_tool_run, update_tool_run_data
from colorama import Style
from agents.planner_executor.execute_tool import execute_tool

# from gcs_utils import file_exists_in_gcs, get_file_from_gcs
from agents.planner_executor.tool_helpers.core_functions import *
from utils import (
    log_str,
    log_msg,
    log_error,
    log_success,
)
from agents.planner_executor.tool_helpers.core_functions import *
import pandas as pd
import traceback
import os


with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

report_assets_dir = env["report_assets_dir"]


# rerun_step_and_dependents function runs the step, the step's parents if needed AND all descendants that depend on this step recursively
# if descendants of children depend on the children, it will keep going down the graph and re running
# we will first re run the step with the given tool_run_id. re running all parents in the process
# then we will run all steps that use the output of that step
async def rerun_step_and_dependents(analysis_id, tool_run_id, steps, global_dict={}):
    async for err, parent_step_id, new_data in rerun_step_and_parents(
        analysis_id, tool_run_id, steps, global_dict=global_dict
    ):
        yield err, parent_step_id, new_data

    # re run steps that use the output of this step
    current_step = None
    for step in steps:
        if step["tool_run_id"] == tool_run_id:
            current_step = step
            break

    for step in steps:
        for output_nm in current_step["outputs_storage_keys"]:
            for _, inp in step["inputs"].items():
                if type(inp) == str and inp.startswith("global_dict."):
                    var = inp.replace("global_dict.", "")
                    if var == output_nm:
                        log_msg(
                            f"Found a step that uses the output of the step that was re run. Rerunning this step."
                        )

                        async for (
                            err,
                            dependent_run_id,
                            new_data,
                        ) in rerun_step_and_dependents(
                            analysis_id,
                            step["tool_run_id"],
                            steps,
                            global_dict=global_dict,
                        ):
                            yield err, dependent_run_id, new_data

                    break


async def rerun_step_and_parents(analysis_id, tool_run_id, steps, global_dict={}):
    # function that will rerun a step
    # find the step with the tool_run_id and it's inputs
    # then it will need to iterate through all inputs of the step then for each input:
    # it will have to check if the input has "global_dict" in it
    # if so it will find the step which produces that output target_step
    # once found, it will find if the dataset exists in the report_assets/datasets folder with the file name target_step["tool_run_id"] + output_storage_key + ".feather"
    # if so, it will load that dataset and replace the global_dict.variable_name reference with the dataset
    # otherwise, it will run the rerun_step function recursively on the target_step

    target_step = None
    for step in steps:
        if step["tool_run_id"] == tool_run_id:
            target_step = step
            break

    if target_step is None:
        yield "Cannot find step with tool_run_id: " + tool_run_id, tool_run_id, None

    print(
        f"{target_step['tool_name']} step has inputs: {log_str(target_step['inputs'])}."
    )

    print("Resolving inputs now")

    for _, input in target_step["inputs"].items():
        # if there's a global_dict.variable_name reference in step["inputs"], replace it with the value from global_dict, if found
        if type(input) == str and input.startswith("global_dict"):
            var = input.replace("global_dict.", "")
            if var in global_dict:
                continue
            # if it doesn't exist in global_dict, find the step that produces that output
            # so find the step that has the output_storage_key that matches the input
            for s in steps:
                log_msg(f"Looking for input {var} for step.")
                if var in s["outputs_storage_keys"]:
                    f_name = s["tool_run_id"] + "_output-" + var + ".feather"
                    err, tool_run_data = await get_tool_run(s["tool_run_id"])

                    if err:
                        log_error(f"Error getting tool run data: {err}")
                        yield err, s["tool_run_id"], None

                    source_tool = tool_run_data["tool_name"]

                    log_msg(
                        f"Looks like input {var} was generated using the tool {source_tool}. Checking if the results exist or the tool has been edited."
                    )

                    # check if the file exists
                    found = False
                    f_path = os.path.join(report_assets_dir, "datasets", f_name)
                    if not tool_run_data["edited"]:
                        if os.path.isfile(f_path):
                            log_msg(f"Input {var} found in the file system.")
                            found = True

                        if found:
                            df = pd.read_feather(f_path)
                            df.name = var
                            global_dict[var] = df

                    if not found or tool_run_data["edited"]:
                        # if file doesn't exist or was unable to be recovered from gcs or file system, or the tool was edited, run the rerun_step function recursively on the target_step
                        if tool_run_data["edited"]:
                            log_error(
                                f"The tool {source_tool} associated with the input {var} was edited. Re running."
                            )
                        else:
                            print(f"Input {var} not found for step. Re running.")

                        # yield a pre run message
                        # that just notifies the front end what is going to be re run
                        yield None, None, {"pre_tool_run_message": s["tool_run_id"]}

                        async for (
                            err,
                            parent_step_id,
                            new_data,
                        ) in rerun_step_and_parents(
                            analysis_id,
                            s["tool_run_id"],
                            steps,
                            global_dict=global_dict,
                        ):
                            yield err, parent_step_id, new_data

                    break

    # once inputs are prepared, actually re run the step
    err, tool_run_data = await get_tool_run(tool_run_id)

    if err:
        log_error(f"Error getting tool run data: {err}{Style.RESET_ALL}")

        yield err, tool_run_id, None

    log_msg(f"Running step {tool_run_id}")

    tool_run_details = tool_run_data.get("tool_run_details")

    # print global_dict keys
    print(f"Global dict currently has keys: {log_str(list(global_dict.keys()))}")

    f_nm = target_step["tool_name"]
    resolved_inputs = {}
    for input_name, val in target_step["inputs"].items():
        resolved_inputs[input_name] = resolve_input(val, global_dict)

    print("Inputs resolved. Running tool: ", f_nm)
    inputs_to_log = []
    for _, inp in resolved_inputs.items():
        if isinstance(inp, pd.DataFrame):
            inputs_to_log.append(
                f"Pandas dataframe with shape {inp.shape} and columns {inp.columns}"
            )
        else:
            inputs_to_log.append(inp)

    log_msg(f"Running tool {f_nm} with inputs {inputs_to_log}")

    # yield a pre run message
    # that just notifies the front end what is going to be re run
    yield None, None, {"pre_tool_run_message": tool_run_id}

    # if this tool is data_fetcher
    # we need to check if the initial inputs to the function have changed
    # or just the SQL query
    if f_nm == "data_fetcher_and_aggregator":
        result = None
        initial_inputs = target_step.get("model_generated_inputs")
        if not initial_inputs:
            initial_inputs = target_step["inputs"]
        # data_fetcher only gives one output so can just save directly
        output_nm = target_step["outputs_storage_keys"][0]
        # there's only one string to compare
        if initial_inputs["question"] == resolved_inputs[
            "question"
        ] and tool_run_details.get("sql"):
            print(f"Data fetcher inputs are the same. Running the SQL instead.")
            print(f"SQL: {tool_run_details.get('sql')}")

            err = None
            result = None
            new_data = None
            try:
                result = await fetch_query_into_df(tool_run_details["sql"])
            except Exception as e:
                err = str(e)
                result = None
                traceback.print_exc()

            if not err:
                # save the result in the global_dict
                global_dict[output_nm] = result
                global_dict[output_nm].name = output_nm
                # first remove any errors
                update_res = await update_tool_run_data(
                    analysis_id,
                    tool_run_id,
                    "error_message",
                    None,
                )
                # update with this new result
                update_res = await update_tool_run_data(
                    analysis_id,
                    tool_run_id,
                    "outputs",
                    {output_nm: {"data": result}},
                )
                if not update_res["success"]:
                    log_error(
                        f"Error saving the outputs of re running step: {update_res['error_message']}"
                    )

                    new_data = None
                    err = update_res["error_message"]
                else:
                    new_data = update_res["tool_run_data"]
                    log_success(f"Successfully saved output of running tool:" + f_nm)
            else:
                # if there was an error, store new tool result with that error
                update_res = await update_tool_run_data(
                    analysis_id, tool_run_id, "error_message", err
                )
                if not update_res["success"]:
                    log_error(f"Error re running step: {update_res['error_message']}")

                else:
                    log_error(
                        f"Had errors, but managed to save output of running tool: "
                        + f_nm
                    )
                    new_data = update_res["tool_run_data"]

            yield err, tool_run_id, new_data
        else:
            print(
                f"Data fetcher inputs have changed or it's a fresh run. Running the function."
            )
            # run the data_fetcher tool normally with the new inputs
            result, signature = await execute_tool(
                "data_fetcher_and_aggregator", resolved_inputs, global_dict
            )

            err = result.get("error_message")
            new_data = None

            # save the result["outputs"]
            if not err:
                global_dict[output_nm] = result["outputs"][0]["data"]
                global_dict[output_nm].name = output_nm

                # first remove any errors from target_step
                target_step["error_message"] = None
                store_res = await store_tool_run(analysis_id, target_step, result)

                if not store_res["success"]:
                    log_error(f"Error re running step: {store_res['error_message']}")

                else:
                    log_success(f"Successfully saved output of running tool: " + f_nm)
                    new_data = store_res["tool_run_data"]

            else:
                # if there was an error, store new tool result with that error
                update_res = await update_tool_run_data(
                    analysis_id, tool_run_id, "error_message", err
                )
                if not update_res["success"]:
                    log_error(f"Error re running step: {update_res['error_message']}")

                else:
                    log_error(
                        f"Had errors, but managed to save output of running tool: "
                        + f_nm
                    )
                    new_data = update_res["tool_run_data"]
                log_error(f"Error re running step: {err}")

            yield err, tool_run_id, new_data

    # else run the code from code_str
    # with the resolved inputs
    else:
        # we will use the code_str that is saved instead of using tool code stored in the db
        # as it might have been edited by the user
        code_str = tool_run_details["code_str"]

        # add a line calling the function and spread the inputs
        # define the function
        err = None
        result = tool_run_details
        new_data = None
        try:
            exec(code_str, globals())
            print(resolved_inputs)
            exec_result = await globals()[f_nm](
                **resolved_inputs, global_dict=global_dict
            )
            err = exec_result.get("error_message")
            result.update(exec_result)

            if not err:
                # remove any previous error_message
                result.pop("error_message", None)
                target_step["error_message"] = None
            else:
                result["error_message"] = err

        except Exception as e:
            err = str(e)
            result["error_message"] = err
            traceback.print_exc()

        store_res = await store_tool_run(analysis_id, target_step, result)

        if not store_res["success"]:
            log_error(f"Error storing step: {store_res['error_message']}")
            err = store_res["error_message"]
        else:
            log_success(f"Successfully saved output of running tool: " + f_nm)
            new_data = store_res["tool_run_data"]

        if not err:
            for i, out in enumerate(target_step["outputs_storage_keys"]):
                data = result["outputs"][i]["data"]
                if data is not None and isinstance(data, pd.DataFrame):
                    global_dict[out] = result["outputs"][i]["data"]
                    global_dict[out].name = out
        else:
            log_error(f"Error re running step: {err}")

        yield err, tool_run_id, new_data

    log_success(f"Finished running tool: " + f_nm)
