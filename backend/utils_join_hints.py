import os

from defog.llm.utils import chat_async
from llm_api import O3_MINI
from pydantic import BaseModel
from request_models import TableDescription
from utils_logging import LOGGER
from utils_md import mk_create_ddl

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BACKEND_DIR, "prompts", "join_hints", "system.md"), "r") as f:
    JOIN_HINTS_SYSTEM_PROMPT = f.read()
with open(os.path.join(BACKEND_DIR, "prompts", "join_hints", "user.md"), "r") as f:
    JOIN_HINTS_USER_PROMPT = f.read()


class ReasonedJoinHints(BaseModel):
    reason: str
    join_keys: list[list[str]]


async def get_join_hints(
    db_name: str,
    metadata: list[dict[str, str]],
    table_descriptions: list[TableDescription],
    instructions: str,
) -> ReasonedJoinHints:
    """
    Get join keys for a database.
    """
    combined_metadata_ddl = mk_create_ddl(metadata, table_descriptions)
    if instructions:
        instructions_str = f"\nYou can use the following instructions where applicable for inferring table relationships within the schema:\n{instructions}"
    else:
        instructions_str = ""
    user_prompt = JOIN_HINTS_USER_PROMPT.format(
        db_name=db_name,
        metadata_str=combined_metadata_ddl,
        instructions=instructions_str,
    )
    messages = [
        {"role": "system", "content": JOIN_HINTS_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    LOGGER.debug(f"Join hints user prompt: {user_prompt}")
    response = await chat_async(
        model=O3_MINI,
        messages=messages,
        max_completion_tokens=16384,
        response_format=ReasonedJoinHints,
    )
    LOGGER.debug(f"{response.output_tokens} tokens, {response.cost_in_cents:.1f} cents, {response.time:.1f} seconds")
    response_content: ReasonedJoinHints = response.content
    join_keys_list = response_content.join_keys
    valid_join_keys_list = validate_join_keys(join_keys_list, metadata)
    response_content.join_keys = valid_join_keys_list
    return response_content


def validate_join_keys(join_keys_list: list[list[str]], metadata: list[dict[str, str]]) -> list[list[str]]:
    """
    Validate join keys against metadata.
    Return a list of valid join keys that are present in the metadata.
    """
    valid_join_keys_list = []
    table_column_names = set()
    for column_md in metadata:
        try:
            table_column_names.add((column_md["table_name"], column_md["column_name"]))
        except KeyError:
            LOGGER.warning(f"Invalid column metadata: {column_md}")
            continue
    if not table_column_names:
        LOGGER.warning("No valid metadata found")
        return []
    for join_keys in join_keys_list:
        valid_join_keys = []
        for join_key in join_keys:
            join_key_split = join_key.rsplit(".", 1)
            if len(join_key_split) != 2:
                LOGGER.warning(f"Invalid join key without table name prepended: {join_key}")
                continue
            table_name, column_name = join_key_split
            if (table_name, column_name) in table_column_names:
                valid_join_keys.append(join_key)
            else:
                LOGGER.warning(f"Join key not found in metadata: {join_key}")
        if len(valid_join_keys) > 1:
            # we only return join keys where there are at least 2 valid columns
            valid_join_keys_list.append(valid_join_keys)
    return valid_join_keys_list
