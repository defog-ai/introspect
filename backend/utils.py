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
