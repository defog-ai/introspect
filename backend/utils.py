from datetime import datetime
import inspect
import re
import json
import trace
import traceback
import pandas as pd
from defog import Defog

import yaml
from colorama import Fore, Style

from openai import AsyncOpenAI
import httpx

import numpy as np
from typing import Optional
from generic_utils import make_request, convert_nested_dict_to_list
import os

openai_api_key = os.environ["OPENAI_API_KEY"]

openai = AsyncOpenAI(api_key=openai_api_key)


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


def get_table_metadata_nested_dict(api_key):
    import requests

    try:
        r = requests.post(
            "https://api.defog.ai/get_metadata", json={"api_key": api_key}
        )

        metadata = r.json()["table_metadata"]
        return {"success": True, "metadata_dict": metadata}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Error getting table metadata. Is your api key correct?",
        }


def get_table_metadata_as_sql_creates_from_json(metadata):
    metadata_sql = ""
    for table_name in metadata:
        metadata_sql += f"CREATE TABLE {table_name} (\n"
        for item in metadata[table_name]:
            metadata_sql += f"\t{item['column_name']} {item['data_type']},"
            if item["column_description"]:
                metadata_sql += f" -- {item['column_description']}"
            metadata_sql += "\n"

        metadata_sql += ");\n\n"
    return metadata_sql


def get_table_metadata_as_sql_creates_from_api_key(api_key):
    import requests

    try:
        r = requests.post(
            "https://api.defog.ai/get_metadata", json={"api_key": api_key}
        )

        metadata = r.json()["table_metadata"]
        metadata_sql = get_table_metadata_as_sql_creates_from_json(metadata)
        return {"success": True, "metadata_sql": metadata_sql}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Error getting table metadata. Is your api key correct?",
        }


def api_response(ran_successfully=False, **extra):
    """Returns a JSON object with the ran_successfully key and any extra keys passed in."""
    return {"ran_successfully": ran_successfully, **extra}


def missing_param_error(param_name):
    """Returns a JSON object with the error_message key and a message saying that the param_name is missing."""
    return api_response(
        error_message=f"Missing parameter in request: {param_name}. Request must contain question, agent, and/or generate_report/get_report params."
    )


def get_db_type():
    defog = Defog()
    return defog.db_type


async def get_metadata(dev=False):
    # check if metadata is stored in ~/.defog/metadata.json
    # if it is, load it
    # if not, make a request to the defog api to get it
    home_dir = os.path.expanduser("~")
    defog_path = os.path.join(home_dir, ".defog")
    if os.path.exists(os.path.join(defog_path, "metadata.json")):
        with open(os.path.join(defog_path, "metadata.json"), "r") as f:
            metadata = json.load(f)
        metadata = convert_nested_dict_to_list(metadata)
        table_metadata_csv = pd.DataFrame(metadata).to_csv(index=False)
        glossary = ""
    else:
        table_metadata_csv = ""
        try:
            # with open(os.path.join(defog_path, "metadata.json"), "r") as f:
            #     table_metadata = json.load(f)
            md = await make_request(
                f"{os.environ.get('DEFOG_BASE_URL')}/get_metadata",
                {
                    "api_key": os.environ.get("DEFOG_API_KEY"),
                    "dev": dev,
                },
            )
            table_metadata = md["table_metadata"]

            # write metadata to file
            with open(os.path.join(defog_path, "metadata.json"), "w") as f:
                json.dump(table_metadata, f)

            metadata = convert_nested_dict_to_list(table_metadata)
            table_metadata_csv = pd.DataFrame(metadata).to_csv(index=False)
            glossary = md["glossary"]
        except Exception as e:
            print(e)
            table_metadata_csv = ""
            glossary = ""

    client_description = "In this assignment, assume that you are a data analyst."

    return {
        "table_metadata_csv": table_metadata_csv,
        "client_description": client_description,
        "glossary": glossary,
    }


def success_str(msg=""):
    return f"{Fore.GREEN}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def error_str(msg=""):
    return f"{Fore.RED}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def log_str(msg=""):
    return f"{Fore.BLUE}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def warn_str(msg=""):
    return f"{Fore.YELLOW}{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def log_success(msg=""):
    print(f"{Fore.GREEN}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


def log_error(msg=""):
    print(f"{Fore.RED}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


def log_msg(msg=""):
    print(f"{Fore.BLUE}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


def log_warn(msg=""):
    print(f"{Fore.YELLOW}{Style.BRIGHT}{msg}{Style.RESET_ALL}")


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
                cleaned_item[key] = value
        cleaned_plan.append(cleaned_item)

    return cleaned_plan


async def execute_code(
    code_snippets: list,  # list of code strings to execute
    fn_name,  # function name to call
    use_globals=False,  # whether to use globals as the sandbox
):
    """
    Runs code string and returns output.
    """
    err = None
    out = None
    try:
        sandbox = {}
        if use_globals:
            sandbox = globals()

        for code in code_snippets:
            exec(code, sandbox)

        # check if test_tool is an async function
        if inspect.iscoroutinefunction(sandbox[fn_name]):
            out = await sandbox[fn_name]()
        else:
            out = sandbox[fn_name]()
    except Exception as e:
        out = None
        err = str(e)
        traceback.print_exc()
    finally:
        return err, out


def snake_case(s):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


class SqlExecutionError(Exception):
    def __init__(self, sql, error_message):
        # Call the base class constructor with the parameters it needs
        super().__init__(f"{error_message}")

        # Now for your custom code...
        self.sql = sql


async def make_request(url, payload):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            json={payload},
        )
    return r
