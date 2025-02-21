from tools.analysis_models import AnswerQuestionFromDatabaseInput, AnswerQuestionFromDatabaseOutput
from utils_sql import generate_sql_query
from defog.query import async_execute_query_once

async def answer_question_from_database(input: AnswerQuestionFromDatabaseInput) -> AnswerQuestionFromDatabaseOutput:
    """
    Given a *single* question for a *single* database, this function will first generate a SQL query to answer the question.
    Then, it will execute the SQL query on the database and return the results.
    """
    question = input.question
    db_name = input.db_name
    
    print(question, flush=True)

    sql_response = await generate_sql_query(
        question=question,
        db_name=db_name,
    )
    sql = sql_response["sql"]

    # execute SQL
    colnames, rows = await async_execute_query_once(db_type=db_type, db_creds=db_creds, query=sql)

    print(colnames, flush=True)
    print(rows[:100], flush=True)

    # known issue: if the query returns way too much data, it may run out of context window limits

    return AnswerQuestionFromDatabaseOutput(sql=sql, colnames=colnames, rows=rows)