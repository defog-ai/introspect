import pandas as pd
import traceback
from agents.planner_executor.tools.all_tools import tools
from utils import (
    SqlExecutionError,
    error_str,
    filter_function_inputs,
    wrap_in_async,
)

import asyncio


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
                return result, tool["input_metadata"]
    # if no tool matches
    return {"error_message": "No tool matches this name"}, {}
