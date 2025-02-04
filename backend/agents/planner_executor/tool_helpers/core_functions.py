import os
from generic_utils import LOGGER
from db_utils import redis_client
from .analysis_prompts import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_SYSTEM_PROMPT,
    DEFAULT_OPENAI_USER_PROMPT,
)
import asyncio

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


async def analyse_data_streaming(question: str, data_csv: str, sql: str, api_key: str):
    """
    Generate a short summary of the results for the given qn, yielding tokens one at a time.
    """
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
        stream=True,
    )

    async for chunk in response:
        if chunk.choices[0].delta.content is not None:
            token = chunk.choices[0].delta.content
            
            if token and token not in ["markdown", "```"]:
                yield token