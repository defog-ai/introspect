from defog.llm.utils import chat_async
from utils_logging import LOGGER
from utils_md import get_metadata, mk_create_ddl
from utils_instructions import get_instructions
from llm_api import GPT_4O
from request_models import ColumnMetadata
import re

with open("./prompts/follow_on_questions/user.md", "r") as f:
    FOLLOW_ON_USER_PROMPT = f.read()

async def generate_follow_on_questions(
    question: str, 
    db_name: str = None, 
    metadata: list[ColumnMetadata] = None,
    instructions: str = None,
    model_name: str = GPT_4O,
) -> list[str]:
    """
    Generate follow-on questions for a given question, using an LLM.
    if db_type, metadata, and instructions are explicitly provided, they are used as is.
    Else, we use the db_name to extract the db_type, metadata, and instructions.
    Returns the generated follow-on questions and the error message if any.
    """
    if metadata is None or len(metadata) == 0:
        metadata = await get_metadata(db_name)
    
    if instructions is None:
        instructions = await get_instructions(db_name)
    
    user_prompt = FOLLOW_ON_USER_PROMPT.format(
        question=question,
        table_metadata_ddl=mk_create_ddl(metadata),
        instructions=instructions
    )

    follow_on_questions = await chat_async(
        model_name,
        messages = [
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=64,
    )
    
    LOGGER.info("Cost of generating follow-on questions: %s", follow_on_questions.cost_in_cents)
    LOGGER.info("Time taken to generate follow-on questions: %s", follow_on_questions.time)

    follow_on_questions = follow_on_questions.content.splitlines()

    # remove all leading digits and spaces in the format 1. or 1)
    follow_on_questions = [re.sub(r"^\d+[.)] ", "", q) for q in follow_on_questions]

    # only return at most 3 follow-on questions
    follow_on_questions = follow_on_questions[:3]

    return follow_on_questions