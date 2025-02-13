from defog.llm.utils import chat_async
from analysis_models import AnswerQuestionFromDatabaseInput, AnswerQuestionFromDatabaseOutput
from generic_utils import make_request
from db_utils import get_db_type_creds
from utils_md import mk_create_ddl
from defog.query import async_execute_query_once

async def answer_question_from_database(input: AnswerQuestionFromDatabaseInput) -> AnswerQuestionFromDatabaseOutput:
    question = input.question
    db_name = input.db_name
    
    db_type, db_creds = await get_db_type_creds(db_name)

    # FOR NOW, JUST GET THESE FROM THE API
    # LATER, WE WILL START STORING THEM IN THE DB

    # get metadata from API
    metadata = (await make_request(
        os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai") + "/get_metadata",
        data={"api_key": db_name},
    ))["table_metadata"]
    ddl_statements = mk_create_ddl(metadata)

    # get instruction manual from API
    glossary = (await make_request(
        os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai") + "/get_instruction_manual",
        data={"api_key": db_name},
    ))

    instruction_manual = glossary["glossary_compulsory"] + "\n".join(glossary["glossary_prunable_units"])

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
                f"*Instruction Manual*\n```{instruction_manual}\n```\n"
            },
        ],
        reasoning_effort="low",
    )
    sql = response.content
    sql = sql.split("```sql")[-1].split(";")[0].replace("```", "").strip()

    # execute SQL
    colnames, rows = await async_execute_query_once(db_type=db_type, db_creds=db_creds, query=sql)

    return AnswerQuestionFromDatabaseOutput(sql=sql, colnames=colnames, rows=rows)