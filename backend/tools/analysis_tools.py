import asyncio
import pandas as pd
from tools.analysis_models import (
    AnswerQuestionFromDatabaseInput,
    AnswerQuestionFromDatabaseOutput,
    GenerateReportFromQuestionInput,
    GenerateReportFromQuestionOutput,
    SynthesizeReportFromQuestionsOutput,
)
from utils_logging import LOG_LEVEL, LOGGER
from utils_md import get_metadata, mk_create_ddl
from utils_sql import generate_sql_query
from db_utils import get_db_type_creds
from defog.llm.utils import chat_async
from defog.query import async_execute_query_once
import uuid


async def text_to_sql_tool(
    input: AnswerQuestionFromDatabaseInput,
) -> AnswerQuestionFromDatabaseOutput:
    """
    Given a *single* question for a *single* database, this function will generate a SQL query to answer the question.
    Then, it will execute the SQL query on the database and return the results.

    IMPORTANT: this function will only take in a single question. Do not try to handle multiple questions in the same call.
    """
    question = input.question
    db_name = input.db_name

    LOGGER.debug(f"Question to answer from database ({db_name}):\n{question}\n")

    try:
        sql_response = await generate_sql_query(
            question=question,
            db_name=db_name,
        )
    except Exception as e:
        error_msg = f"Error generating SQL: {e}. Rephrase the question by incorporating specific details of the error to address it."
        LOGGER.error(error_msg)
        return AnswerQuestionFromDatabaseOutput(question=question, error=error_msg)
    sql = sql_response["sql"]

    # execute SQL
    db_type, db_creds = await get_db_type_creds(db_name)
    try:
        colnames, rows = await async_execute_query_once(
            db_type=db_type, db_creds=db_creds, query=sql
        )
    except Exception as e:
        error_msg = f"Error executing SQL: {e}. Rephrase the question by incorporating specific details of the error to address it."
        LOGGER.error(error_msg)
        return AnswerQuestionFromDatabaseOutput(
            question=question, sql=sql, error=error_msg
        )

    if LOG_LEVEL == "DEBUG":
        LOGGER.debug(f"Column names:\n{colnames}\n")
        first_20_rows_str = "\n".join([str(row) for row in rows[:20]])
        LOGGER.debug(f"First 20 rows:\n{first_20_rows_str}\n")

    # aggregate data if too large
    max_rows_displayed = 50
    if len(rows) > max_rows_displayed:
        agg_question = (
            question
            + f" Aggregate or limit the data appropriately or place the data in meaningful buckets such that the result is within a reasonable size (max {max_rows_displayed} rows) and useful for analysis."
        )

        try:
            agg_sql_response = await generate_sql_query(
                question=agg_question,
                db_name=db_name,
            )
        except Exception as e:
            error_msg = f"Error generating aggregate SQL: {e}. Rephrase the question by incorporating specific details of the error to address it."
            LOGGER.error(error_msg)
            return AnswerQuestionFromDatabaseOutput(question=question, error=error_msg)
        agg_sql = agg_sql_response["sql"]

        db_type, db_creds = await get_db_type_creds(db_name)
        try:
            colnames, rows = await async_execute_query_once(
                db_type=db_type, db_creds=db_creds, query=agg_sql
            )
        except Exception as e:
            error_msg = f"Error executing aggregate SQL: {e}. Rephrase the question by incorporating specific details of the error to address it."
            LOGGER.error(error_msg)
            return AnswerQuestionFromDatabaseOutput(
                question=question, sql=agg_sql, error=error_msg
            )
        sql = agg_sql

        if LOG_LEVEL == "DEBUG":
            LOGGER.debug(f"Aggregate column names:\n{colnames}\n")
            first_5_rows_str = "\n".join([str(row) for row in rows[:5]])
            LOGGER.debug(f"First 5 aggregate rows:\n{first_5_rows_str}\n")

    # construct df and then convert to json string
    df_truncated = False
    result_df = pd.DataFrame(rows, columns=colnames)
    if len(rows) > max_rows_displayed:
        result_df = result_df.head(max_rows_displayed)
        df_truncated = True
    result_json = result_df.to_json(orient="records", double_precision=4)
    columns = result_df.columns.tolist()
    if result_json == "[]":
        result_json = "No data retrieved. Consider rephrasing the question or generating a new question. Pay close attention to column names and column descriptions in the database schema to ensure you are fetching the right data. If necessary, first retrieve the unique values of the column(s) or first few rows of the table to better understand the data."

    return AnswerQuestionFromDatabaseOutput(
        analysis_id=str(uuid.uuid4()),
        question=question,
        sql=sql,
        columns=columns,
        rows=result_json,
        df_truncated=df_truncated,
    )


async def generate_report_from_question(
    input: GenerateReportFromQuestionInput,
) -> GenerateReportFromQuestionOutput:
    """
    Given an initial question for a single database, this function will call
    text_to_sql_tool() to answer the question.
    Then, it will use the output to generate a new question, and call
    text_to_sql_tool() again.
    It will continue to do this until the LLM model decides to stop.
    """
    try:
        tools = [text_to_sql_tool]
        metadata = await get_metadata(input.db_name)
        metadata_str = mk_create_ddl(metadata)
        response = await chat_async(
            model=input.model,
            tools=tools,
            messages=[
                {"role": "developer", "content": "Formatting re-enabled"},
                {
                    "role": "user",
                    "content": f"""I would like you to create a comprehensive analysis for answering this question: {input.question}

Look in the database {input.db_name} for your answers, and feel free to continue asking multiple questions from the database if you need to. I would rather that you ask a lot of questions than too few. Do not ask the exact same question twice. Always ask new questions or rephrase the previous question if it led to an error.

The database schema is below:
```sql
{metadata_str}
```

Try to aggregate data in clear and understandable buckets. Please give your final answer as a descriptive report.

For each point that you make in the report, please include all the relevant analysis IDs in brackets that was used to generate the data for it e.g. [ID: analysis_id_1, analysis_id_2].
""",
                },
            ],
        )
        sql_answers = []
        for tool_output in response.tool_outputs:
            if tool_output.get("name") == "text_to_sql_tool":
                result = tool_output.get("result")
                if not result or not isinstance(
                    result, AnswerQuestionFromDatabaseOutput
                ):
                    LOGGER.error(f"Invalid tool output: {tool_output}")
                    continue
                sql_answers.append(result)
        return GenerateReportFromQuestionOutput(
            report=response.content,
            sql_answers=sql_answers,
            tool_outputs=response.tool_outputs,
        )
    except Exception as e:
        LOGGER.error(f"Error in generate_report_from_question:\n{e}")
        return GenerateReportFromQuestionOutput(
            report="Error in generating report from question",
            sql_answers=[],
        )


async def synthesize_report_from_questions(
    input: GenerateReportFromQuestionInput,
) -> SynthesizeReportFromQuestionsOutput:
    """
    Given an initial question for a single database, this function will call
    generate_report_from_question() multiple times in parallel to generate a report.
    It will continue to do this until the LLM model decides to stop.
    """
    try:
        tasks = [generate_report_from_question(input) for _ in range(input.num_reports)]
        responses = await asyncio.gather(*tasks)
        metadata = await get_metadata(input.db_name)
        metadata_str = mk_create_ddl(metadata)
        user_prompt = f"""Your task is to synthesize a series of reports into a final report.

# Context
These reports were generated by querying a database with a series of questions.
The schema for the database is as follows:
{metadata_str}

# Task
Synthesize these intermediate reports done by a group of independent analysts into a final report by combining the insights from each of the reports provided.

You should attempt to get the most useful insights from each report, without repeating the insights across reports. Please ensure that you get the actual data insights from these reports, and not just methodologies.

You must cite the relevant analysis IDs in brackets [] for each key insight in the report.

Here are the reports to synthesize:
"""
        for response in responses:
            user_prompt += f"\n\n{response.report}"
        messages = [
            {"role": "developer", "content": "Formatting re-enabled"},
            {"role": "user", "content": user_prompt},
        ]
        synthesis_response = await chat_async(
            model=input.model,
            messages=messages,
        )
        return SynthesizeReportFromQuestionsOutput(
            synthesized_report=synthesis_response.content,
            report_answers=responses,
        )
    except Exception as e:
        LOGGER.error(f"Error in synthesize_report_from_questions:\n{e}")
        return SynthesizeReportFromQuestionsOutput(
            synthesized_report="Error in synthesizing report from questions",
            report_answers=[],
        )
