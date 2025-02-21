from defog.llm.utils import chat_async
from utils_logging import LOGGER
from utils_md import get_metadata, mk_create_ddl
from utils_instructions import get_instructions
from llm_api import GPT_4O, GPT_4O_MINI
from request_models import ColumnMetadata
from pydantic import BaseModel
from typing import Literal
import warnings

warnings.simplefilter(action="ignore", category=SyntaxWarning)

with open("./prompts/clarify_question/user.md", "r") as f:
    CLARIFY_QUESTION_USER_PROMPT = f.read()

with open("./prompts/classify_question/system.md", "r") as f:
    CLASSIFY_QUESTION_SYSTEM_PROMPT = f.read()


async def generate_clarification(
    question: str,
    db_name: str = None,
    metadata: list[ColumnMetadata] = None,
    instructions: str = None,
    model_name: str = GPT_4O,
) -> str:
    """
    Generate clarification for a given question, using an LLM.
    if db_type, metadata, and instructions are explicitly provided, they are used as is.
    Else, we use the db_name to extract the db_type, metadata, and instructions.
    Returns the generated clarification and the error message if any.
    """
    if metadata is None or len(metadata) == 0:
        metadata = await get_metadata(db_name)

    if instructions is None:
        instructions = await get_instructions(db_name)

    user_prompt = CLARIFY_QUESTION_USER_PROMPT.format(
        question=question,
        table_metadata_ddl=mk_create_ddl(metadata),
        instructions=instructions,
    )

    clarifications = await chat_async(
        model=model_name,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=128,
    )

    LOGGER.info("Cost of generating clarification: %s", clarifications.cost_in_cents)
    LOGGER.info("Time taken to generate clarification: %s", clarifications.time)

    return clarifications.content


async def turn_clarifications_into_statement(
    clarifications: list[str], model_name: str = GPT_4O
) -> str:
    """
    Turn a list of clarifications into a single statement.
    """
    questions_and_answers = "\n".join(
        [
            f'Question: {q["question"]}\nAnswer: {q.get("response", "No response")}'
            for q in clarifications
        ]
    )

    user_prompt = f"""Here is a Question / Answer statement that I got from a user: {questions_and_answers}

Please convert this into a single statement.

Here are some examples of these Question / Answer statements, and your expected responses:
Question: What do you mean by "best" restaurants?" Answer: those with the most reviews Response: Return the restaurants with the most number of ratings.
Question: What do you mean by the "worst" players? Answer: those with the lowest total scores Response: Return the players with the lowest total scores"""

    statement = await chat_async(
        model=GPT_4O_MINI,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=128,
    )

    LOGGER.info("Cost of generating clarification: %s", statement.cost_in_cents)
    LOGGER.info("Time taken to generate clarification: %s", statement.time)

    return statement.content


async def generate_assignment_understanding(
    analysis_id, clarification_questions, db_name
):
    """
    Generates the assignment understanding from the clarification questions.

    And stores in the analyses table.
    """
    # get the assignment understanding aka answers to clarification questions
    assignment_understanding = None

    LOGGER.info(f"Clarification questions: {clarification_questions}")

    if len(clarification_questions) > 0:
        try:
            assignment_understanding = await turn_clarifications_into_statement(
                clarification_questions, db_name
            )
        except Exception as e:
            LOGGER.error(e)
            assignment_understanding = ""

    LOGGER.info(f"Assignment understanding: {assignment_understanding}")

    return assignment_understanding


class QuestionType(BaseModel):
    question_type: Literal["analysis", "edit-chart"]
    default_open_tab: Literal["table", "chart"]


async def classify_question_type(
    question: str,
) -> QuestionType:
    """
    Classify the question type.
    """
    response = await chat_async(
        model=GPT_4O_MINI,
        messages=[
            {"role": "system", "content": CLASSIFY_QUESTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Here is the user's question: `{question}`"},
        ],
        max_completion_tokens=128,
        response_format=QuestionType,
    )

    LOGGER.info("Cost of classifying question type: %s", response.cost_in_cents)
    LOGGER.info("Time taken to classify question type: %s", response.time)

    return response.content.model_dump()
