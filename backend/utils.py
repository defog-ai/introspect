import base64
import inspect
import re
import json
import traceback
from typing import Optional
from colorama import Fore, Style

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)


# custom list class with a overwrite_key attribute
class YieldList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overwrite_key = None


def replace_whitespace(s):
    pattern = re.compile(r'",\s*"')
    return re.sub(pattern, '", "', s)


def fix_JSON(json_message=None):
    result = json_message
    json_message = replace_whitespace(json_message)
    try:
        # First, try to load the JSON string as is
        result = json.loads(json_message)
    except json.JSONDecodeError as e:
        try:
            # If the JSON string can't be loaded, it means there are unescaped characters
            # Use Python's string escape to escape the string
            escaped_message = json_message.encode("unicode_escape").decode("utf-8")
            # Try loading the JSON string again
            result = json.loads(escaped_message)
        except Exception as e_inner:
            # If it still fails, print the error
            print("Error while trying to fix JSON string: ", str(e_inner))
            return None
    except Exception as e:
        print("Unexpected error: ", str(e))
        return None
    return result


def api_response(ran_successfully=False, **extra):
    """Returns a JSON object with the ran_successfully key and any extra keys passed in."""
    return {"ran_successfully": ran_successfully, **extra}


def missing_param_error(param_name):
    """Returns a JSON object with the error_message key and a message saying that the param_name is missing."""
    return api_response(
        error_message=f"Missing parameter in request: {param_name}. Request must contain question, agent, and/or generate_report/get_report params."
    )


def success_str(msg=""):
    return f"{Fore.GREEN}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def error_str(msg=""):
    return f"{Fore.RED}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def log_str(msg=""):
    return f"{Fore.BLUE}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def warn_str(msg=""):
    return f"{Fore.YELLOW}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def log_success(msg=""):
    logging.info(f"{Fore.GREEN}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


def log_error(msg=""):
    logging.error(f"{Fore.RED}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


def log_msg(msg=""):
    logging.info(f"{Fore.BLUE}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


def log_warn(msg=""):
    logging.warning(f"{Fore.YELLOW}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


simple_tool_types = {
    "DBColumn": "Column name",
    "DBColumnList": "List of column names",
    "pandas.core.frame.DataFrame": "Dataframe",
    "str": "String",
    "int": "Integer",
    "float": "Float",
    "bool": "Boolean",
    "list[str]": "List of strings",
    "list": "List",
    "DropdownSingleSelect": "String",
}


def create_simple_tool_types(_type):
    # if type starts with DBColumnList...
    if _type.startswith("DBColumnList"):
        return "List of column names"
    if _type.startswith("ListWithDefault"):
        return "List"

    else:
        return simple_tool_types.get(_type, _type)


def get_clean_plan(analysis_data):
    generated_plan = analysis_data.get("gen_steps", {}).get("steps", [])
    cleaned_plan = []
    for item in generated_plan:
        cleaned_item = {}
        for key, value in item.items():
            if key in [
                "tool_name",
                "model_generated_inputs",
                "outputs_storage_keys",
                "done",
                "error_message",
            ]:
                # if key is model_generated_inputs, just change it to inputs
                if key == "model_generated_inputs":
                    cleaned_item["inputs"] = value
                else:
                    cleaned_item[key] = value
        cleaned_plan.append(cleaned_item)

    return cleaned_plan


def snake_case(s):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


class SqlExecutionError(Exception):
    def __init__(self, sql, error_message):
        # Call the base class constructor with the parameters it needs
        super().__init__(f"{error_message}")

        # Now for your custom code...
        self.sql = sql


def deduplicate_columns(df: pd.DataFrame):
    # de-duplicate column names
    # if the same column name exists more than once, add a suffix
    deduplicated_df = df.copy()
    columns = deduplicated_df.columns.tolist()
    seen = {}
    for i, item in enumerate(columns):
        if item in seen:
            columns[i] = f"{item}_{seen[item]}"
            seen[item] += 1
        else:
            seen[item] = 1

    deduplicated_df.columns = columns

    return deduplicated_df


def filter_function_inputs(fn, inputs):
    """
    Used to filter down a dict's keys to only the parameters that are required by a function
    Creates a filtering function that can be run on a dict
    Which will filter the dict's keys based on the return value (True or False)
    of the filter function
    If the function takes kwargs, we always return true from the function
    Otherwise, we check if the key is in the function's parameters
    """
    # if a function takes kwargs, then we will
    sig = inspect.signature(fn)
    params = sig.parameters.values()
    has_kwargs = any([True for p in params if p.kind == p.VAR_KEYWORD])
    f = lambda _: True

    if not has_kwargs:
        param_names = [p.name for p in params]
        f = lambda key: key in param_names

    return {k: v for k, v in inputs.items() if f(k)}, f


def wrap_in_async(fn):
    """
    If a function isn't async, wrap it in an async function for create_Task to work
    """
    wrapped_fn = fn
    if not inspect.iscoroutinefunction(fn):

        async def async_fn(**kwargs):
            return fn(**kwargs)

        wrapped_fn = async_fn

    return wrapped_fn


def add_indent(level=1):
    return "...." * level


async def execute_code(
    code_snippets: str | list[str],  # string or list of code strings to execute
    fn_name: Optional[str],  # function name to call
    sandbox: Optional[dict] = None,  # custom sandbox to use
    use_globals: bool = False,  # whether to import globals into the sandbox or not
    default_imports: list[str] = [],  # default imports for the sandbox. List of strings
    args: Optional[list] = [],  # args to pass to the function
    kwargs: Optional[dict] = {},  # kwargs to pass to the function
):
    """
    Runs code string and returns output.
    """
    err = None
    out = None

    if type(code_snippets) != str and type(code_snippets) != list:
        raise ValueError("code_snippets should be a string or list of strings")

    if type(code_snippets) == str:
        code_snippets = [code_snippets]

    if not fn_name:
        raise ValueError("fn_name must be provided.")

    try:
        _sandbox = sandbox or {}
        if use_globals:
            _sandbox = globals().update(_sandbox)

        if len(default_imports) > 0:
            exec("\n".join(default_imports), _sandbox)

        for code in code_snippets:
            exec(code, _sandbox)

        # check if test_tool is an async function
        if inspect.iscoroutinefunction(_sandbox[fn_name]):
            out = await _sandbox[fn_name](*args, **kwargs)
        else:
            out = _sandbox[fn_name](*args, **kwargs)
    except Exception as e:
        out = None
        err = str(e)
        traceback.print_exc()
    finally:
        return err, out


def encode_image(image_path):
    """
    Encodes an image to base64.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def longest_substring_overlap(s1, s2, min_substr_len_match):
    """
    If the longest overlap is greater than or equal to min_substr_len_match,
    return True and matched string, otherwise return False and longest matched string.

    Args:
        s1 (str): First string.
        s2 (str): Second string.
        min_substr_len_match (int): Minimum substring length to consider as a match.

    Returns:
        bool: True if the minimum substring length match is reached, otherwise False.
        str: The overlapping substring.
    """
    max_overlap = 0
    overlap_string = ""

    for i in range(len(s1)):
        for j in range(len(s2)):
            k = 0
            while i + k < len(s1) and j + k < len(s2) and s1[i + k] == s2[j + k]:
                k += 1
            if k > max_overlap:
                max_overlap = k
                overlap_string = s1[i : i + k]

    return max_overlap >= min_substr_len_match, overlap_string
