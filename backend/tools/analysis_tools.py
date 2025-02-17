from defog.llm.utils import chat_async
from tools.analysis_models import AnswerQuestionFromDatabaseInput, AnswerQuestionFromDatabaseOutput
from db_utils import get_db_type_creds
from utils_md import mk_create_ddl, get_metadata
from utils_instructions import get_instructions
from utils_golden_queries import get_closest_golden_queries
from utils_embedding import get_embedding
from defog.query import async_execute_query_once

async def answer_question_from_database(input: AnswerQuestionFromDatabaseInput) -> AnswerQuestionFromDatabaseOutput:
    """
    Given a *single* question for a *single* database, this function will first generate a SQL query to answer the question.
    Then, it will execute the SQL query on the database and return the results.
    """
    question = input.question
    db_name = input.db_name
    
    print(question, flush=True)

    db_type, db_creds = await get_db_type_creds(db_name)

    # get metadata from API
    metadata = await get_metadata(db_name)
    ddl_statements = mk_create_ddl(metadata)

    # get instruction manual from API
    instructions = await get_instructions(db_name)

    # get embedding of the question, and then get the closest golden queries
    embedding = await get_embedding(text=question)
    golden_queries = await get_closest_golden_queries(db_name=db_name, question_embedding=embedding)
    print(golden_queries, flush=True)

    # get SQL from LLM
    response = await chat_async(
        model="o3-mini",
        messages=[
            {
                "role": "user",
                "content": f"Generate a SQL query that answers this question: `{question}`. Please return only the SQL query, nothing else.\n"
                f"The SQL query must be valid and executable on a {db_type} database.\n"
                "Here are DDL statements and instruction manual associated with this database: \n"
                f"*DDL Statements*\n```sql\n{ddl_statements}\n```\n\n"
                f"*Instruction Manual*\n```{instructions}\n```\n"
            },
        ],
        reasoning_effort="low",
    )
    sql = response.content
    sql = sql.split("```sql")[-1].split(";")[0].replace("```", "").strip()

    # execute SQL
    colnames, rows = await async_execute_query_once(db_type=db_type, db_creds=db_creds, query=sql)

    print(colnames, flush=True)
    print(rows[:100], flush=True)

    # known issue: if the query returns way too much data, it may run out of context window limits

    return AnswerQuestionFromDatabaseOutput(sql=sql, colnames=colnames, rows=rows)