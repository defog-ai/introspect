from datetime import datetime
import re
import json
import traceback
import pandas as pd
from defog import Defog

import yaml
from colorama import Fore, Style
# import pika
import redis

env = None

with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

redis_host = env["redis_server_host"]

redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)


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


# clean yaml strings
# change double quotes to single quotes inside strings


def get_metadata():
    table_metadata_csv = redis_client.get("integration:metadata")
    client_description = "In this assignment, assume that you are a medical data analyst who is working with lab sample data for T cells of cancer patients."
    glossary = """- If you encounter the term `variable_value` in the metadata, it refers specifically to the column `variable_value`, and not a generic value. NEVER ask a question like "which variable name are you referring to"
- Match the terms used by users to the terms used in the database schema. For example, if a user asks for Regulatory T Cells, and the database uses the term Tregs, then modify your response accordingly.
- Recall that the term `reportable` refers to quantitative variables
- When asking clarifying questions, ONLY use the information in the `column_name` column"""
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


# async def add_files_to_rabbitmq_queue(files):
#     print("Files for rabbit mq:", files)
#     err = None
#     try:
#         parameters = pika.URLParameters("amqp://admin:admin@agents-rabbitmq/")

#         connection = pika.BlockingConnection(parameters)
#         channel = connection.channel()

#         # Declare a queue
#         queue_name = "gcs"
#         channel.queue_declare(queue=queue_name)

#         channel.basic_publish(
#             exchange="",
#             routing_key=queue_name,
#             body=json.dumps(files),
#         )
#     except Exception as e:
#         print("Error adding files to rabbitmq queue")
#         traceback.print_exc()
#         err = str(e)
#     finally:
#         return err
