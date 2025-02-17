import time
import traceback
from datetime import datetime

import sqlparse
from auth_utils import validate_user_request
from db_utils import get_db_type_creds
from defog.llm.utils import chat_async
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from llm_api import O3_MINI
from request_models import GenerateSQLQueryRequest, QuestionAnswer
from utils_embedding import get_embedding
from utils_golden_queries import get_closest_golden_queries
from utils_instructions import get_instructions
from utils_logging import LOGGER, log_timings, save_timing
from utils_md import get_metadata, mk_create_ddl
from utils_sql import add_hard_filters

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Query Generation"],
)

with open("./prompts/generate_sql/system.md", "r") as f:
    GENERATE_SQL_SYSTEM_PROMPT = f.read()

with open("./prompts/generate_sql/user.md", "r") as f:
    GENERATE_SQL_USER_PROMPT = f.read()


@router.post("/generate_sql_query")
async def generate_sql_query(request: GenerateSQLQueryRequest):
    """
    Generate a chat response based on a query.
    1. Retrieve metadata and instructions
    2. Get the question embedding and then closest golden queries
    3. Format the messages for the LLM
    4. Generate SQL using the appropriate model
    5. Post-generation processing (cleaning, adding hard filters) and logging
    """
    t_start, timings = time.time(), []
    try:

        if not request.metadata:
            metadata = await get_metadata(request.db_name)
        else:
            metadata = request.metadata
        metadata_str = mk_create_ddl(metadata)

        if not request.instructions:
            instructions = await get_instructions(request.db_name)
        else:
            instructions = request.instructions

        db_type, _ = await get_db_type_creds(request.db_name)

        t_start = save_timing(t_start, "Retrieved metadata and instructions", timings)

        question_embedding = await get_embedding(request.question)
        t_start = save_timing(t_start, "Retrieved question embedding", timings)

        golden_queries = await get_closest_golden_queries(
            request.db_name, question_embedding, request.num_golden_queries
        )
        golden_queries_prompt = ""
        for i, golden_query in enumerate(golden_queries):
            golden_queries_prompt += f"Example question {i+1}: {golden_query.question}\nExample query {i+1}:\n```sql\n{golden_query.sql}\n```\n\n"
        t_start = save_timing(
            t_start, f"Retrieved {len(golden_queries)} golden queries", timings
        )

        # Create the messages
        messages = get_messages(
            db_type=db_type,
            date_today=datetime.today().strftime("%Y-%m-%d"),
            instructions=instructions,
            user_question=request.question,
            table_metadata_ddl=metadata_str,
            system_prompt=GENERATE_SQL_SYSTEM_PROMPT,
            user_prompt=GENERATE_SQL_USER_PROMPT,
            previous_context=request.previous_context,
            golden_queries_prompt=golden_queries_prompt,
        )
        model = O3_MINI if not request.model_name else request.model_name

        # Generate the query
        query = await chat_async(
            model=model, messages=messages, max_completion_tokens=16384
        )
        t_start = save_timing(t_start, "Generated query", timings)
        LOGGER.info("latency of query in seconds: " + "{:.2f}".format(query.time) + "s")
        LOGGER.info(
            "cost of query in cents: " + "{:.2f}".format(query.cost_in_cents) + "¢"
        )
        ans = query.content
        ans = ans.split("```sql", 1)[-1].split(";", 1)[0].replace("```", "").strip()
        ans = clean_generated_query(ans)

        # Add hard filters if present
        hard_filters = request.hard_filters
        if hard_filters and len(hard_filters) > 0:
            ans = add_hard_filters(ans, hard_filters)
        t_start = save_timing(t_start, "Added hard filters", timings)

        log_timings(timings)
        return {
            "sql": ans,
        }
    except Exception as e:
        if timings:
            log_timings(timings)
        LOGGER.error(f"[generate_sql_query] ERROR: {e}")
        LOGGER.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})


def get_messages(
    db_type: str,
    date_today: str,
    instructions: str,
    user_question: str,
    table_metadata_ddl: str,
    system_prompt: str,
    user_prompt: str,
    previous_context: list[QuestionAnswer] | None = None,
    golden_queries_prompt: str = "",
):
    """
    Creates messages for the chatbot.
    """
    system_prompt = system_prompt.format(db_type=db_type, date_today=date_today)
    previous_messages = []
    if previous_context and len(previous_context) > 0:
        for question_answer in previous_context:
            previous_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Create a SQL query for answering the following question: `{question_answer.question}`."
                        "Note that subsequent questions are a follow-on question from one, and you should keep this in mind when creating the query for future questions."
                    ),
                }
            )
            previous_messages.append(
                {
                    "role": "assistant",
                    "content": f"```sql\n{question_answer.answer};\n```",
                }
            )

    user_prompt = user_prompt.format(
        user_question=user_question,
        table_metadata_ddl=table_metadata_ddl,
        instructions=instructions,
        golden_queries_prompt=golden_queries_prompt,
    )

    messages = (
        [{"role": "system", "content": system_prompt}]
        + previous_messages
        + [{"role": "user", "content": user_prompt}]
    )
    for message in messages:
        LOGGER.debug(f"{message['role']}: {message['content']}")
    return messages


def clean_generated_query(query: str):
    """
    Clean up the generated query by
    - formatting the query using sqlparse
    - fixing common problems in LLM-powered query generation with post-processing heuristics

    KNOWN ISSUES: the division fix will only work with Postgres/Redshift/Snowflake/Databricks. It might not work with other databases.
    """

    query = sqlparse.format(query, reindent_aligned=True)

    # if the string `< =` is present, replace it with `<=`. Similarly for `> =` and `>=`
    query = query.replace("< =", "<=").replace("> =", ">=")

    # if the string ` / NULLIF (` is present, replace it with `/ NULLIF ( 1.0 * `.
    # This is a fix for ensuring that the denominator is always a float in division operations.
    query = query.replace("/ NULLIF (", "/ NULLIF (1.0 * ")
    return query
