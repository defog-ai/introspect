from typing import Dict, List
import base64
import os
from generic_utils import make_request, LOGGER
import os
import json
from db_utils import redis_client
from .analysis_prompts import (
    DEFAULT_BEDROCK_MODEL,
    DEFAULT_BEDROCK_PROMPT,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_SYSTEM_PROMPT,
    DEFAULT_OPENAI_USER_PROMPT,
)
import asyncio

analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


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
        or "create" in query
    ):
        return False

    return True


# resolves an input to a tool
# by replacing global_dict references to the actual variable values
def resolve_input(inp, global_dict):
    # if inp is list, replace each element in the list with call to resolve_input
    if isinstance(inp, list):
        resolved_inputs = []
        for inp in inp:
            resolved_inputs.append(resolve_input(inp, global_dict))

        return resolved_inputs

    elif isinstance(inp, str) and inp.startswith("global_dict."):
        variable_name = inp.split(".")[1]
        print(inp)
        return global_dict.get(variable_name)

    else:
        if isinstance(inp, str):
            # if only numbers, return float
            if inp.isnumeric():
                return float(inp)

            # if None as a string after stripping, return None
            if inp.strip() == "None":
                return None
            return inp

        return inp


async def analyse_data(question: str, data_csv: str, sql: str, api_key: str) -> str:
    """
    Generate a short summary of the results for the given qn.
    """
    if os.environ.get("ANALYZE_DATA", "no") != "yes":
        return ""
    else:
        if os.environ.get("ANALYZE_DATA_MODEL") == "defog":
            analysis = await make_request(
                url=DEFOG_BASE_URL + "/agents/analyse_data",
                data={
                    "api_key": api_key,
                    "question": question,
                    "sql": sql,
                    "data_csv": data_csv,
                },
            )
            return analysis.get("model_analysis", "")
        elif os.environ.get("ANALYZE_DATA_MODEL") == "bedrock":
            import boto3

            bedrock = boto3.client(service_name="bedrock-runtime")
            model_id = redis_client.get("bedrock_model_id")
            if model_id is None or model_id == "":
                LOGGER.warning("BEDROCK_MODEL not set, skipping data analysis")
                model_id = DEFAULT_BEDROCK_MODEL
            accept = "application/json"
            contentType = "application/json"
            model_prompt = redis_client.get("bedrock_model_prompt")
            if model_prompt is None or model_prompt == "":
                model_prompt = DEFAULT_BEDROCK_PROMPT

            body = json.dumps(
                {
                    "prompt": model_prompt.format(
                        question=question, sql=sql, data_csv=data_csv
                    ),
                    "max_gen_len": 600,
                    "temperature": 0,
                    "top_p": 1,
                }
            )

            response = await asyncio.to_thread(
                bedrock.invoke_model,
                body=body,
                modelId=model_id,
                accept=accept,
                contentType=contentType,
            )
            model_response = json.loads(response["body"].read())
            LOGGER.info(model_response)
            generation = model_response["generation"]
            return generation
        elif os.environ.get("ANALYZE_DATA_MODEL") == "openai":
            # if OPENAI_API_KEY is not set, return an error
            if os.environ.get("OPENAI_API_KEY") is None:
                return "You are using openai for analysing data, but OPENAI_API_KEY is not set. Please set it in the environment variables."
            from openai import AsyncOpenAI

            openai = AsyncOpenAI()
            system_prompt = redis_client.get("openai_system_prompt")
            if system_prompt is None or system_prompt == "":
                system_prompt = DEFAULT_OPENAI_SYSTEM_PROMPT

            user_prompt = redis_client.get("openai_user_prompt")
            if user_prompt is None or user_prompt == "":
                user_prompt = DEFAULT_OPENAI_USER_PROMPT

            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt.format(
                        question=question, sql=sql, data_csv=data_csv
                    ),
                },
            ]

            response = await openai.chat.completions.create(
                model=DEFAULT_OPENAI_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=600,
                seed=42,
            )

            generation = response.choices[0].message.content.strip()
            return generation
