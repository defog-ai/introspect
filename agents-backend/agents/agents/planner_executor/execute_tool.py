from .tool_helpers.all_tools import tools
from defog import Defog
import pandas as pd
from typing import Tuple
import traceback
import inspect


def parse_function_signature(param_signatures):
    """
    Given a dictionary of function signature, return a list of all the parameters
    with name, default values and types.
    """
    params = []
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
            p_type = "str"
        else:
            p_type = str(p_type)[8:-2]

        if type(p_default_val) == type:
            p_default_val = str(p_default_val)[8:-2]

        params.append(
            {
                "name": p_name,
                "default": p_default_val,
                "type": p_type,
            }
        )
    return params


async def execute_tool(tool_name, tool_inputs, global_dict={}):
    print(f"Executing tool: {tool_name}")
    print(f"Tool inputs: {tool_inputs}")
    # print(f"Global dict: {global_dict}")
    result = {}
    for tool in tools:
        if tool["name"] == tool_name:
            fn = tool["fn"]
            try:
                # expand tool inputs
                result = await fn(*tool_inputs, global_dict=global_dict)

            # if keyerror, then error string will not have "key error" in it but just the name of the key
            except KeyError as e:
                print(f"Error for tool {tool_name}: KeyError, key not found {e}")
                traceback.print_exc()
                result = {
                    "error_message": f"KeyError: key not found {e}. This might be due to missing columns in the generated data from earlier. You might need to run data fetcher again to make sure the required columns is in the data. "
                }
            except Exception as e:
                print(f"Error for tool {tool_name}: {e}")
                traceback.print_exc()
                result = {"error_message": str(e)[:300]}
            finally:
                # if result has no code_str, use inspect.getsource to get code_str
                if "code_str" not in result:
                    if "ask_prompt" not in inspect.getsource(fn):
                        result["code_str"] = inspect.getsource(fn)

                return result, parse_function_signature(
                    inspect.signature(fn).parameters
                )
    # if no tool matches
    return {"error_message": "No tool matches this name"}, {}
