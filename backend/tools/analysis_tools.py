import asyncio
from openai.types import file_content
import pandas as pd
import os
from tools.analysis_models import (
    AnswerQuestionInput,
    AnswerQuestionFromDatabaseInput,
    AnswerQuestionFromDatabaseOutput,
    AnswerQuestionViaPDFCitationsInput,
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
from typing import Callable
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from anthropic import AsyncAnthropic


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

    LOGGER.info(f"Question to answer from database ({db_name}):\n{question}\n")

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

    result_json = result_df.to_json(orient="records", double_precision=4, date_format="iso")
    columns = result_df.columns.astype(str).tolist()
    if result_json == "[]":
        error_msg = "No data retrieved. Consider rephrasing the question or generating a new question. Pay close attention to column names and column descriptions in the database schema to ensure you are fetching the right data. If necessary, first retrieve the unique values of the column(s) or first few rows of the table to better understand the data."
    else:
        error_msg = ""

    return AnswerQuestionFromDatabaseOutput(
        analysis_id=str(uuid.uuid4()),
        question=question,
        sql=sql,
        columns=columns,
        rows=result_json,
        df_truncated=df_truncated,
        error=error_msg,
    )


async def web_search_tool(
    input: AnswerQuestionInput,
) -> str:
    """
    Given a user question, this tool will visit the top ranked pages on Google and extract information from them.
    It will then concisely answer the question based on the extracted information, and will return the answer as a string.
    It should be used when a question cannot be directly answered by the database, or when additional context can be provided to the user by searching the web.
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    google_search_tool = Tool(
        google_search = GoogleSearch()
    )
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        config=GenerateContentConfig(
            tools=[google_search_tool],
            response_modalities=["TEXT"],
        ),
        contents=input.question + "\nNote: you must **always** use the google search tool to answer questions - no exceptions.",
    )
    sources = [{"source": chunk.web.title, "url": chunk.web.uri} for chunk in response.candidates[0].grounding_metadata.grounding_chunks]
    return {
        "answer_summary": response.text,
        "reference_sources": sources
    }


async def pdf_citations_tool(
    input: AnswerQuestionViaPDFCitationsInput,
) -> str:
    """
    Given a user question and the id of a PDF, this tool will attempt to answer the question from the data that is available in the PDF.
    It will return the answer as a string.
    """
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    file_content_messages = []
    for file_id in input.pdf_files:
        pdf_content = await get_pdf_page_content(file_id)
        title = pdf_content.title
        base_64_pdf = pdf_content.base_64_pdf
        file_content_messages.append(
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base_64_pdf
                },
                "title": title,
                "citations": {"enabled": True},
                "cache_control": {"type": "ephemeral"}
            }
        )
    
    messages = [
        {
            "role": "user",
            "content": file_content_messages + [
                {
                    "type": "text",
                    "content": input.question,
                }
            ],
        }
    ]

    response = await client.messages.create(
        model="claude-3-7-sonnet-latest",
        messages=messages,
    )
    return response.content

async def load_custom_tools():
    """
    Load and dynamically import custom tools for a specific database from the database.
    Returns a list of callable functions.
    """
    from sqlalchemy.future import select
    from db_config import get_defog_internal_session
    from db_models import CustomTools
    from typing import Dict, Any, Callable, Awaitable
    import importlib
    import sys
    import re
    import ast
    import pydantic
    
    custom_tools = []
    
    # Get custom tools from database
    async with get_defog_internal_session() as session:
        result = await session.execute(
            select(CustomTools).where(
                CustomTools.is_enabled == True
            )
        )
        tools_db = result.all()
    
    if not tools_db:
        return []
    
    # Helper function to validate tool code safely
    def validate_tool_code(code: str) -> bool:
        """
        Validate that the tool code doesn't contain unsafe operations.
        """
        # Parse the code into an AST
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False
        
        # Check for unsafe operations (imports, eval, exec, etc.)
        unsafe_calls = ['eval', 'exec', '__import__', 'subprocess', 'os.system', 
                        'os.popen', 'os.spawn', 'os.fork', 'pty.spawn']
        
        for node in ast.walk(tree):
            # Check for import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Check import targets
                if isinstance(node, ast.ImportFrom) and node.module and any(
                    unsafe in node.module for unsafe in ['subprocess', 'os', 'sys', 'pty', 'shutil']
                ):
                    return False
                
                # Check imported names
                if isinstance(node, ast.ImportFrom) and node.names:
                    for name in node.names:
                        if name.name in ['system', 'popen', 'spawn', 'eval', 'exec']:
                            return False
            
            # Check for unsafe function calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec']:
                return False
            
            # Check for attribute access that could be unsafe
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                # Get the full attribute chain
                attr_chain = []
                obj = node.func
                while isinstance(obj, ast.Attribute):
                    attr_chain.append(obj.attr)
                    obj = obj.value
                
                if isinstance(obj, ast.Name):
                    attr_chain.append(obj.id)
                    attr_path = '.'.join(reversed(attr_chain))
                    
                    # Check if the attribute path contains unsafe operations
                    if any(unsafe in attr_path for unsafe in unsafe_calls):
                        return False
        
        return True
    
    # Process each tool
    for tool_row in tools_db:
        tool_record = tool_row[0]  # Extract the actual ORM object
        
        # Skip if code validation fails
        if not validate_tool_code(tool_record.tool_code):
            LOGGER.error(f"Tool {tool_record.tool_name} contains unsafe operations and will not be loaded")
            continue
        
        try:
            # Create a unique module name for this tool
            module_name = f"custom_tool_{tool_record.tool_name}_{hash(tool_record.tool_code)}"
            
            # Create a new module
            module = type(sys)(module_name)
            
            # Add required imports to the module's namespace
            module.__dict__.update({
                'pd': pd,
                'LOGGER': LOGGER,
                'BaseModel': importlib.import_module('pydantic').BaseModel,
                'Field': importlib.import_module('pydantic').Field,
                'Optional': importlib.import_module('typing').Optional,
                'List': importlib.import_module('typing').List,
                'Dict': importlib.import_module('typing').Dict,
                'Any': importlib.import_module('typing').Any,
                'get_metadata': importlib.import_module('utils_md').get_metadata,
                'mk_create_ddl': importlib.import_module('utils_md').mk_create_ddl,
                'get_db_type_creds': importlib.import_module('db_utils').get_db_type_creds,
                'async_execute_query_once': importlib.import_module('defog.query').async_execute_query_once,
                'uuid': uuid,
            })
            
            # Add the module to sys.modules
            sys.modules[module_name] = module
            
            # Execute the input model code in the module's namespace
            if tool_record.input_model:
                exec(tool_record.input_model, module.__dict__)
            
            # Execute the tool code in the module's namespace
            exec(tool_record.tool_code, module.__dict__)
            
            # Get the tool function from the module
            # We expect the function to have the same name as the tool_name
            tool_func = module.__dict__.get(tool_record.tool_name)
            
            if not tool_func or not callable(tool_func):
                # If the function isn't found by name, look for the first async function in the module
                for name, obj in module.__dict__.items():
                    if callable(obj) and hasattr(obj, '__code__') and obj.__code__.co_flags & 0x80:  # Check if async
                        tool_func = obj
                        break
            
            if tool_func:
                # Add tool documentation from the database
                tool_func.__doc__ = tool_record.tool_description
                
                # Add the tool to the list
                custom_tools.append(tool_func)
            else:
                LOGGER.error(f"Could not find callable function in tool {tool_record.tool_name}")
        
        except Exception as e:
            LOGGER.error(f"Error loading custom tool {tool_record.tool_name}: {e}")
    
    return custom_tools


async def generate_report_from_question(
    db_name: str,
    model: str,
    question: str,
    clarification_responses: str,
    post_tool_func: Callable
) -> GenerateReportFromQuestionOutput:
    """
    Given an initial question for a single database, this function will call
    text_to_sql_tool() to answer the question.
    Then, it will use the output to generate a new question, and call
    text_to_sql_tool() again.
    It will continue to do this until the LLM model decides to stop.
    """
    try:
        # Start with default tools
        tools = [text_to_sql_tool, web_search_tool]
        
        # Load custom tools for this database
        custom_tools = await load_custom_tools()
        tools.extend(custom_tools)
        metadata = await get_metadata(db_name)
        metadata_str = mk_create_ddl(metadata)
        response = await chat_async(
            model=model,
            tools=tools,
            messages=[
                # {"role": "developer", "content": "Formatting re-enabled"},
                {
                    "role": "user",
                    "content": f"""I would like you to create a comprehensive analysis for answering this question: {question}

Look in the database {db_name} for your answers, and feel free to continue asking multiple questions from the database if you need to. I would rather that you ask a lot of questions than too few. Do not ask the exact same question twice. Always ask new questions or rephrase the previous question if it led to an error.
{clarification_responses}
The database schema is below:
```sql
{metadata_str}
```

Try to aggregate data in clear and understandable buckets. Please give your final answer as a descriptive report.
""",
                },
            ],
            post_tool_function=post_tool_func,
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
            tool_outputs=[],
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
