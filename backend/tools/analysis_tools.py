from tools.analysis_models import (
    AnswerQuestionFromDatabaseInput,
    AnswerQuestionFromDatabaseOutput,
)
from utils_logging import LOG_LEVEL, LOGGER
from utils_sql import generate_sql_query
from db_utils import get_db_type_creds
from defog.query import async_execute_query_once


async def answer_question_from_database(
    input: AnswerQuestionFromDatabaseInput,
) -> AnswerQuestionFromDatabaseOutput:
    """
    Given a *single* question for a *single* database, this function will first generate a SQL query to answer the question.
    Then, it will execute the SQL query on the database and return the results.
    """
    question = input.question
    db_name = input.db_name

    LOGGER.debug(f"Question to answer from database ({db_name}):\n{question}\n")

    sql_response = await generate_sql_query(
        question=question,
        db_name=db_name,
    )
    sql = sql_response["sql"]

    # execute SQL
    db_type, db_creds = await get_db_type_creds(db_name)
    colnames, rows = await async_execute_query_once(
        db_type=db_type, db_creds=db_creds, query=sql
    )

    if LOG_LEVEL == "DEBUG":
        LOGGER.debug(f"Column names:\n{colnames}\n")
        first_20_rows_str = "\n".join([str(row) for row in rows[:20]])
        LOGGER.debug(f"First 20 rows:\n{first_20_rows_str}\n")

    # known issue: if the query returns way too much data, it may run out of context window limits

    return AnswerQuestionFromDatabaseOutput(sql=sql, colnames=colnames, rows=rows)
