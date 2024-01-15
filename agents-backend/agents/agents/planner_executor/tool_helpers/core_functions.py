from typing import Dict, List
import tiktoken
from datetime import date
import traceback
import pandas as pd
from sqlalchemy import create_engine
from defog import Defog
from defog.query import execute_query

# these are needed for the exec_code function
from uuid import uuid4
from sksurv.preprocessing import OneHotEncoder
from sksurv.nonparametric import kaplan_meier_estimator
from sksurv.datasets import get_x_y
from sksurv.compare import compare_survival
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sklearn.model_selection import GridSearchCV, KFold
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import redis
import json
import yaml

with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

redis_host = env["redis_server_host"]
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

encoding = tiktoken.encoding_for_model("gpt-4-0613")

DEFOG_API_KEY = "genmab-survival-test"

# make sure the query does not contain any malicious commands like drop, delete, etc.
def safe_sql(query):
    if query is None:
        return False

    query = query.lower()
    if (
        "drop" in query
        or "delete" in query
        or "truncate" in query
        or "append" in query
        or "insert" in query
        or "update" in query
    ):
        return False

    return True

async def fetch_query_into_df(sql_query: str) -> pd.DataFrame:
    """
    Runs a sql query and stores the results in a pandas dataframe.
    """

    # important note: this is currently a blocking call
    # TODO: add an option to the defog library to make this async
    
    db_type = redis_client.get("integration:db_type")
    db_creds = redis_client.get("integration:db_creds")
    if db_creds is not None:
        db_creds = json.loads(db_creds)
    
    colnames, data, new_sql_query = execute_query(
        sql_query, DEFOG_API_KEY, db_type, db_creds, retries=0
    )
    df = pd.DataFrame(data, columns=colnames)

    # if this df has any columns that have lists, remove those columns
    for col in df.columns:
        if df[col].apply(type).eq(list).any():
            df = df.drop(col, axis=1)

    df.sql_query = sql_query
    return df


async def execute_code(codestr):
    """
    Executes the code in a string. Returns the error or results.
    """
    err = None
    analysis = None
    full_data = None
    try:
        # add some imports to the codestr
        exec(codestr)
        analysis, full_data = await locals()["exec_code"]()
        full_data.code_str = codestr
    except Exception as e:
        traceback.print_exc()
        err = e
        analysis = None
        full_data = None
    finally:
        return err, analysis, full_data


def estimate_tokens_left(messages: List[Dict], model: str) -> int:
    """
    Returns an estimate of the number of tokens left for generation based on the
    messages generated so far and the model used.
    """
    encoding = tiktoken.encoding_for_model(model)
    total_tokens = 0
    for msg in messages:
        num_tokens = len(encoding.encode(msg["content"]))
        total_tokens += num_tokens
    if model == "gpt-3.5-turbo":
        return 4000 - total_tokens
    elif "gpt-4" in model:
        return 8000 - total_tokens
    else:
        raise ValueError(f"Unsupported model {model}")


# resolves an input to a tool
# by replacing global_dict references to the actual variable values
def resolve_input(input, global_dict):
    # if input is list, replace each element in the list with call to resolve_input
    if isinstance(input, list):
        resolved_inputs = []
        for inp in input:
            resolved_inputs.append(resolve_input(inp, global_dict))

        return resolved_inputs

    elif isinstance(input, str) and input.startswith("global_dict."):
        variable_name = input.split(".")[1]
        return global_dict[variable_name]

    else:
        if isinstance(input, str):
            # if only numbers, return float
            if input.isnumeric():
                return float(input)

            # if None as a string after stripping, return None
            if input.strip() == "None":
                return None
            return input

        return input
