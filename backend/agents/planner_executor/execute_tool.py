import pandas as pd
import traceback
from agents.planner_executor.tools.all_tools import tools
from utils import (
    SqlExecutionError,
    wrap_in_async,
)
from utils_logging import LOGGER

import asyncio


async def execute_tool(function_name, tool_function_inputs):
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
    result = {}

    for key in tools:
        tool = tools[key]
        if tool["function_name"] == function_name:
            # add param types to import

            fn = tool["fn"]
            wrapped_fn = wrap_in_async(fn)
            task = asyncio.create_task(wrapped_fn(**tool_function_inputs))
            try:
                # expand tool inputs
                # if it takes more than 120 seconds, then timeout
                result = await asyncio.wait_for(task, timeout=300)
            except asyncio.TimeoutError:
                LOGGER.error(f"Error for tool {function_name}: TimeoutError")
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
                LOGGER.error(f"Error for tool {function_name}: KeyError, key not found {e}")
                traceback.print_exc()
                result = {
                    "error_message": f"KeyError: key not found {e}. This might be due to missing columns in the generated data from earlier. You might need to run data fetcher again to make sure the required columns is in the data."
                }
            except IndexError as e:
                LOGGER.error(f"Error for tool {function_name}: IndexError: {e}")
                traceback.print_exc()
                result = {
                    "error_message": f"IndexError: index not found {e}. This might be due to empty dataframes from columns in the generated data from earlier. You might need to run data fetcher again to make sure the query is correct."
                }
            except SqlExecutionError as e:
                print("\n\nHAD SQL ERROR\n", str(e), flush=True)
                result = {"sql": e.sql, "error_message": str(e)}
            except Exception as e:
                LOGGER.error(f"Error for tool {function_name}: {e}")
                traceback.print_exc()
                result = {"error_message": str(e)[:300]}
            finally:
                return result, tool["input_metadata"]
    # if no tool matches
    return {"error_message": "No tool matches this name"}, {}
