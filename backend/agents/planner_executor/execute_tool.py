import re
import pandas as pd
import traceback
import inspect
from agents.planner_executor.tools.all_tools import tools
from utils import (
    SqlExecutionError,
    error_str,
    warn_str,
    filter_function_inputs,
    wrap_in_async,
)

# from db_utils import get_all_tools
import asyncio
from tool_code_utilities import default_top_level_imports


def parse_function_signature(param_signatures, fn_name):
    """
    Given a dictionary of function signature, return a list of all the parameters
    with name, default values and types.
    """
    params = {}
    for p in param_signatures:
        # ignore kwargs
        if p == "kwargs" or p == "global_dict":
            continue
        p_name = param_signatures[p].name
        p_default_val = param_signatures[p].default

        if p_default_val is param_signatures[p].empty:
            p_default_val = None

        p_type = param_signatures[p].annotation
        if p_type is param_signatures[p].empty:
            warn_str(
                "No type annotation for parameter "
                + p_name
                + " in "
                + fn_name
                + ". Assuming type is str."
            )
            p_type = "str"
        else:
            # if p_type starts with <class, then take the class name
            if str(p_type).startswith("<class"):
                p_type = str(p_type)[8:-2]
            # if it contains "DBColumn", then just say "DBColumn"
            if (
                str(p_type)
                == "agents.planner_executor.tool_helpers.tool_param_types.DBColumn"
            ):
                p_type = "DBColumn"
            # if it's a list of DBColumn, then include the number of elements
            if str(p_type).startswith(
                "agents.planner_executor.tool_helpers.tool_param_types.DBColumnList_"
            ):
                # get index of DBColumnList_ and use string from there till end
                match = re.search("DBColumnList_", str(p_type)).start()
                p_type = str(p_type)[match:]

            # if DropdownSingleSelect, then just say "DropDownSingleSelect"
            if (
                str(p_type)
                == "agents.planner_executor.tool_helpers.tool_param_types.DropdownSingleSelect"
            ):
                p_type = "DropdownSingleSelect"

        # if default value type is a class, convert to string
        if type(p_default_val) == type:
            p_default_val = str(p_default_val)[8:-2]

        params[p_name] = {
            "name": p_name,
            "default": p_default_val,
            "type": p_type,
        }

    return params


async def execute_tool(function_name, tool_function_inputs, global_dict={}):
    print(f"Executing tool: {function_name} with inputs: {tool_function_inputs}")
    inputs_to_log = []
    for _, inp in tool_function_inputs.items():
        if isinstance(inp, pd.DataFrame):
            inputs_to_log.append(
                f"Pandas dataframe with shape {inp.shape} and columns {inp.columns}"
            )
        else:
            inputs_to_log.append(inp)
    print(f"Tool inputs: {inputs_to_log}")
    # print(f"Global dict: {global_dict}")
    result = {}

    # err, tools = await get_all_tools()
    # if err:
    #     return {"error_message": f"Error getting tools: {err}"}, {}

    for key in tools:
        tool = tools[key]
        if tool["function_name"] == function_name:
            # add param types to import

            code = tool["code"]

            # add a few default top level imports so input types can be defined in the function definition
            code = default_top_level_imports + "\n" + code

            # exec(code, globals())
            # fn = globals()[function_name]
            fn = tool["fn"]

            if tool_function_inputs.get("global_dict"):
                tool_function_inputs["global_dict"].update(global_dict)
            else:
                tool_function_inputs["global_dict"] = global_dict

            filtered_inputs, _ = filter_function_inputs(fn, tool_function_inputs)

            wrapped_fn = wrap_in_async(fn)

            task = asyncio.create_task(wrapped_fn(**filtered_inputs))
            try:
                # expand tool inputs
                # if it takes more than 120 seconds, then timeout
                result = await asyncio.wait_for(task, timeout=300)
            except asyncio.TimeoutError:
                print(error_str(f"Error for tool {function_name}: TimeoutError"))
                result = {
                    "error_message": f"Tool {tool} was taking more 2 mins to run and was stopped. This might be due to a long running SQL query, or creating a very complex plot. Please try filtering your data for a faster execution"
                }

                task.cancel()
                try:
                    # Wait for the task cancellation to complete, catching any cancellation exceptions
                    await task
                except asyncio.CancelledError:
                    print("\n\nTask was successfully cancelled upon timeout")

            # if keyerror, then error string will not have "key error" in it but just the name of the key
            except KeyError as e:
                print(
                    error_str(
                        f"Error for tool {function_name}: KeyError, key not found {e}"
                    )
                )
                traceback.print_exc()
                result = {
                    "error_message": f"KeyError: key not found {e}. This might be due to missing columns in the generated data from earlier. You might need to run data fetcher again to make sure the required columns is in the data."
                }
            except IndexError as e:
                print(error_str(f"Error for tool {function_name}: IndexError: {e}"))
                traceback.print_exc()
                result = {
                    "error_message": f"IndexError: index not found {e}. This might be due to empty dataframes from columns in the generated data from earlier. You might need to run data fetcher again to make sure the query is correct."
                }
            except SqlExecutionError as e:
                print("\n\nHAD SQL ERROR\n", str(e), flush=True)
                result = {"sql": e.sql, "error_message": str(e)}
            except Exception as e:
                print(error_str(f"Error for tool {function_name}: {e}"))
                traceback.print_exc()
                result = {"error_message": str(e)[:300]}
            finally:
                result["code_str"] = tool["code"]

                return result, tool["input_metadata"]
    # if no tool matches
    return {"error_message": "No tool matches this name"}, {}
