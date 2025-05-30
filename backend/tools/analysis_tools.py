import pandas as pd
import os
import numpy as np
import json
import uuid
import time
from typing import Any, Callable

from tools.analysis_models import (
    AnswerQuestionInput,
    AnswerQuestionFromDatabaseInput,
    ThinkToolInput,
    AnswerQuestionFromDatabaseOutput,
    AnswerQuestionViaPDFCitationsInput,
    GenerateReportFromQuestionOutput,
)
from utils_logging import LOG_LEVEL, LOGGER
from utils_md import get_metadata, mk_create_ddl
from utils_sql import generate_sql_query
from db_utils import get_db_type_creds
from defog.llm.utils import chat_async
from defog.llm.web_search import web_search_tool as web_search
from defog.llm.citations import citations_tool
from defog.llm.code_interp import code_interpreter_tool as code_interpreter
from defog.query import async_execute_query_once
from anthropic import AsyncAnthropic
from utils_oracle import get_pdf_content


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

    sql_response = await generate_sql_query(
        question=question,
        db_name=db_name,
    )
    if sql_response.get("error"):
        error_msg = f"Error generating SQL: {sql_response['error']}."
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

        agg_sql_response = await generate_sql_query(
            question=agg_question,
            db_name=db_name,
        )
        if agg_sql_response.get("error"):
            error_msg = f"Error generating aggregate SQL: {agg_sql_response['error']}."
            LOGGER.error(error_msg)
            return AnswerQuestionFromDatabaseOutput(question=question, error=error_msg)
        agg_sql = agg_sql_response["sql"]

        res = await get_db_type_creds(db_name)
        if not res:
            error_msg = f"Database '{db_name}' not found. Check if the database name is correct or if credentials have been configured."
            LOGGER.error(error_msg)
            return AnswerQuestionFromDatabaseOutput(question=question, sql=agg_sql, error=error_msg)
        db_type, db_creds = res
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

    # if a column name is repeated, append the column name with a number
    colnames = result_df.columns.tolist()
    for col in colnames:
        if colnames.count(col) > 1:
            for i in range(len(colnames)):
                if colnames[i] == col:
                    colnames[i] = f"{col}_{i}"
    result_df.columns = colnames

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
) -> dict[str, Any]:
    """
    Given a user question, this tool will visit the top ranked pages on Google and extract information from them.
    It will then concisely answer the question based on the extracted information, and will return the answer as a JSON, with a "reference_sources" key that lists the web pages from which the information was extracted and an "answer" key that contains the concisely answered question.
    It should be used when a question cannot be directly answered by the database, or when additional context can be provided to the user by searching the web.
    """
    LOGGER.info(f"Web search tool called with question: {input.question}")
    
    # if gemini_api_key is set, use gemini
    # else, use openai
    try:
        if os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
            model = "gpt-4.1"
            LOGGER.info("Using OpenAI for web search tool")
        elif os.environ.get("GEMINI_API_KEY"):
            provider = "gemini"
            model = "gemini-2.5-pro-preview-05-06"
            LOGGER.info("Using Gemini for web search tool")
        elif os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
            model = "claude-4-sonnet-20250514"
            LOGGER.info("Using Anthropic for web search tool")
        else:
            raise ValueError("No API key found for web search tool")

        response = await web_search(
            provider=provider,
            model=model,
            question=input.question + "\nNote: you must **always** use the google search tool to answer questions - no exceptions.",
            max_tokens=4096,
        )

        sources = response["websites_cited"]
        search_results = response["search_results"]
        
        return {
            "analysis_id": str(uuid.uuid4()),
            "answer": search_results,
            "reference_sources": sources
        }
    except Exception as e:
        LOGGER.error(f"Error running web search tool: {e}")
        return {
            "answer": "Error running web search tool",
            "error": str(e),
            "reference_sources": []
        }
    
    


async def pdf_citations_tool(
    input: AnswerQuestionViaPDFCitationsInput,
):
    """
    Given a user question and a list of PDF ids, this tool will attempt to answer the question from the information that is available in the PDFs.
    It will return the answer as a JSON.
    """
    LOGGER.info(f"Calling PDF Citations tool with question: {input.question} and PDF ids: {input.pdf_files}")
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    file_content_messages = []
    for file_id in input.pdf_files:
        pdf_content = await get_pdf_content(file_id)
        title = pdf_content["file_name"]
        base_64_pdf = pdf_content["base64_data"]
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
            "content": file_content_messages + [{"type": "text", "text": input.question + "\nUse citations to back up your answer"}],
        }
    ]

    response = await client.messages.create(
        model="claude-4-sonnet-20250514",
        messages=messages,
        max_tokens=4096,
    )
    return {
        "analysis_id": str(uuid.uuid4()),
        "citations": [item.to_dict() for item in response.content]
    }


async def think_tool(
    input: ThinkToolInput,
) -> str:
    """
    Think about how to best perform the task requested by the user – given the available tools, the previous context, and the user's question. This tool should be used a) at the start, b) when complex reasoning is needed, and c) near the end of the task to see if more analyses are needed for a higher quality final output.
    """
    LOGGER.info(f"Thinking about task: {input.thought}")
    return input.thought


async def code_interpreter_tool(
    input: AnswerQuestionFromDatabaseInput,
) -> dict[str, Any]:
    """
    Code Interpreter tool that performs data analysis on database results using pandas, numpy, scipy, etc.
    
    This tool works by:
    1. Taking a data analysis question and database name
    2. Generating SQL queries to fetch the necessary data
    3. Using AI to generate Python code for the analysis
    4. Safely executing the code in a controlled environment
    5. Returning the analysis results
    
    The tool supports using pandas, numpy, scipy, and statsmodels libraries for analysis.

    Important: it does not support plotting or visualizations of any kind.
    """
    question = input.question
    db_name = input.db_name
    
    LOGGER.info(f"Code Interpreter analyzing: {question} (database: {db_name})")
    
    # Step 1: Generate SQL to fetch the data needed for analysis
    sql_generation_prompt = f"""
    I need to perform the following data analysis: "{question}"

Generate a SQL query that will fetch the appropriate data from the database to answer this question.
The query should:
1. Retrieve all relevant columns needed for the analysis
2. Include any necessary filters, joins, or aggregations
3. Return a complete dataset that can be analyzed with pandas and other Python libraries

The query should NOT do any data cleaning, preprocessing, or transformations. Those will be done in Python later.
"""
    
    # Use text_to_sql_tool to fetch data
    sql_input = AnswerQuestionFromDatabaseInput(
        question=sql_generation_prompt,
        db_name=db_name
    )
    sql_result = await text_to_sql_tool(sql_input)
    
    # Check for errors in SQL generation or execution
    if sql_result.error:
        LOGGER.error(f"Error fetching data for code interpreter: {sql_result.error}")
        return {
            "analysis_id": str(uuid.uuid4()),
            "question": question,
            "error": f"Failed to fetch data: {sql_result.error}",
            "code": "",
            "result": "",
        }
    
    # Step 2: Prepare data for analysis
    if not sql_result.rows or sql_result.rows == "[]":
        LOGGER.error("No data returned from SQL query")
        return {
            "analysis_id": str(uuid.uuid4()),
            "question": question,
            "error": "No data returned from the database. Please refine your question.",
            "code": sql_result.sql,
            "result": "",
        }
    
    csv_string = pd.DataFrame(
        json.loads(sql_result.rows),
        columns=sql_result.columns
    ).to_csv(index=False)

    if os.environ.get("GEMINI_API_KEY"):
        provider = "gemini"
        model = "gemini-2.5-pro-preview-05-06"
        LOGGER.info("Using Gemini for code interpreter tool")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        model = "claude-4-sonnet-20250514"
        LOGGER.info("Using Anthropic for code interpreter tool")
    elif os.environ.get("OPENAI_API_KEY"):
        provider = "openai"
        model = "gpt-4.1"
        LOGGER.info("Using OpenAI for code interpreter tool")
    else:
        raise ValueError("No API key found for OpenAI, Anthropic, or Gemini. Please set one of these environment variables.")
    
    try:
        t1 = time.time()
        code_interpreter_result = await code_interpreter(
            question=question,
            provider=provider,
            model=model,
            csv_string=csv_string
        )
        t2 = time.time()
        LOGGER.info(f"Code interpreter tool took {t2 - t1} seconds")
        
        return {
            "analysis_id": str(uuid.uuid4()),
            "question": question,
            "code": code_interpreter_result["code"],
            "result": code_interpreter_result["output"],
            "error": "",
            "sql": sql_result.sql
        }

    except Exception as e:
        LOGGER.error(f"Error running code interpreter: {e}")
        return {
            "analysis_id": str(uuid.uuid4()),
            "question": question,
            "error": f"Error running code interpreter: {e}",
            "code": "",
            "result": "",
        }


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

    def validate_input_model(code: str) -> bool:
        """Validate that the provided input model code is safe."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False

        unsafe_calls = [
            'eval', 'exec', '__import__', 'subprocess', 'os.system',
            'os.popen', 'os.spawn', 'os.fork', 'pty.spawn'
        ]

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False

            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in unsafe_calls:
                return False

            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attr_chain = []
                obj = node.func
                while isinstance(obj, ast.Attribute):
                    attr_chain.append(obj.attr)
                    obj = obj.value

                if isinstance(obj, ast.Name):
                    attr_chain.append(obj.id)
                    attr_path = '.'.join(reversed(attr_chain))

                    if any(unsafe in attr_path for unsafe in unsafe_calls):
                        return False

        has_model = any(
            isinstance(node, ast.ClassDef) and
            any(
                (isinstance(base, ast.Name) and base.id == 'BaseModel') or
                (isinstance(base, ast.Attribute) and base.attr == 'BaseModel')
                for base in node.bases
            )
            for node in tree.body
        )

        return has_model
    
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

            # Execute the input model code in a restricted namespace
            if tool_record.input_model:
                if not validate_input_model(tool_record.input_model):
                    LOGGER.error(f"Input model for tool {tool_record.tool_name} is unsafe and will be skipped")
                    continue

                namespace = {
                    'BaseModel': module.__dict__['BaseModel'],
                    'Field': module.__dict__['Field'],
                    '__builtins__': {},
                }
                before_keys = set(namespace.keys())
                exec(tool_record.input_model, namespace)
                for key in set(namespace.keys()) - before_keys:
                    module.__dict__[key] = namespace[key]
            
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

async def multi_agent_report_generation(
    db_name: str,
    question: str,
    clarification_responses: str,
    post_tool_func: Callable,
    pdf_file_ids: list[int] = [],
    use_websearch: bool = False,
) -> GenerateReportFromQuestionOutput:
    """
    Implements a multi-agent approach to report generation using specialized agents
    for analysis, evaluation, and final report writing.
    
    This approach uses three phases:
    1. Data Collection & Analysis: Gather comprehensive data and initial analysis
    2. Evaluation & Refinement: Evaluate findings and identify gaps or follow-up questions
    3. Report Synthesis: Create a final polished report from all gathered insights
    
    Each phase uses Claude 3.7 Sonnet with specific instructions for its role.
    """
    try:
        # Setup tools for all agents
        tools = [text_to_sql_tool, think_tool, code_interpreter_tool]
        pdf_instruction = ""
        if use_websearch:
            tools.append(web_search_tool)
        
        if len(pdf_file_ids) > 0:
            tools.append(pdf_citations_tool)
            pdf_instruction = f"\nThe following PDF file IDs can be searched to help generate your answer: {pdf_file_ids}\n"
        
        # Load custom tools for this database
        custom_tools = await load_custom_tools()
        tools.extend(custom_tools)
        
        # Get database metadata
        metadata = await get_metadata(db_name)
        metadata_str = mk_create_ddl(metadata)
        
        # Record all SQL answers throughout the process
        all_sql_answers = []
        all_tool_outputs = []
        
        LOGGER.info("Starting multi-agent report generation - Phase 1: Data Collection & Analysis")
        
        # PHASE 1: DATA COLLECTION & ANALYSIS
        analyst_response = await chat_async(
            provider="anthropic",
            model="claude-4-sonnet-20250514",
            tools=tools,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a specialized data analyst responsible for collecting comprehensive data to answer a user's question. Your goal is to gather all relevant data by asking thorough and diverse questions of the database. 

You should:
1. Break down complex questions into multiple targeted database queries
2. Explore different angles and perspectives on the question
3. Gather both high-level aggregate data and specific details
4. Look for unexpected patterns or anomalies
5. Ensure you investigate all relevant tables in the schema
6. Run follow-up queries based on initial findings to go deeper
7. Cite sources for all data and insights in the final report

The database schema is:
```sql
{metadata_str}
```"""
                },
                {
                    "role": "user",
                    "content": f"""I need comprehensive data analysis for this question: {question}

Use the database {db_name}, web search (if appropriate), and any PDF files to thoroughly research this question. Ask multiple questions to explore different aspects. Dig deeper into initial findings to uncover insights, patterns and anomalies.

{clarification_responses}
{pdf_instruction}

Provide structured analysis with your key findings after collecting sufficient data. DO NOT write a final report yet - focus on gathering comprehensive data and initial insights.
"""
                }
            ],
            post_tool_function=post_tool_func,
        )
        
        # Extract SQL answers from the analyst phase
        for tool_output in analyst_response.tool_outputs:
            all_tool_outputs.append(tool_output)
            if tool_output.get("name") == "text_to_sql_tool":
                result = tool_output.get("result")
                if result and isinstance(result, AnswerQuestionFromDatabaseOutput):
                    all_sql_answers.append(result)
        
        LOGGER.info("Phase 1 complete. Starting Phase 2: Evaluation & Refinement")
        
        # PHASE 2: EVALUATION & REFINEMENT
        # Prepare the context from Phase 1 for the evaluator
        evaluator_context = f"""
ORIGINAL QUESTION: {question}
{clarification_responses}

DATA ANALYSIS FINDINGS:
{analyst_response.content}
"""
        
        evaluator_response = await chat_async(
            provider="openai",
            model="o4-mini",
            tools=tools,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a critical evaluator responsible for identifying gaps in data analysis and ensuring comprehensive coverage of a question. 

Your tasks are to:
1. Identify any missing information or unexplored angles
2. Suggest specific follow-up questions that would strengthen the analysis
3. Point out any contradictions or areas needing validation
4. Ensure all parts of the original question have been addressed
5. Consider whether additional context (time periods, demographics, etc.) is needed

The database schema is:
```sql
{metadata_str}
```
The database name is {db_name}

{pdf_instruction}
"""
                },
                {
                    "role": "user",
                    "content": f"""Review the following data analysis and identify any gaps, missing perspectives, or follow-up questions needed to fully answer the original question.

{evaluator_context}

First identify what's missing or could be improved, then use database queries to fill these specific gaps. Focus on 2-4 high-value follow-up questions that would significantly improve the analysis.
"""
                }
            ],
            post_tool_function=post_tool_func,
        )
        
        # Extract additional SQL answers from the evaluator phase
        for tool_output in evaluator_response.tool_outputs:
            all_tool_outputs.append(tool_output)
            if tool_output.get("name") == "text_to_sql_tool":
                result = tool_output.get("result")
                if result and isinstance(result, AnswerQuestionFromDatabaseOutput):
                    all_sql_answers.append(result)
        
        LOGGER.info("Phase 2 complete. Starting Phase 3: Report Synthesis with Citations")
        
        # PHASE 3: REPORT SYNTHESIS WITH CITATIONS
        # Prepare document sources from tool outputs
        
        # Initialize Anthropic client
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        # Create document content for each tool output (as separate documents)
        document_contents = []
        for idx, output in enumerate(all_tool_outputs):
            tool_name = output.get("name", "Unknown")
            
            # Get the ID for this tool call
            # check if result is a dict and has an analysis_id key
            if isinstance(output.get("result"), dict):
                analysis_id = output.get("result", {}).get("analysis_id", "Unknown")
            # else, check if it is AnswerQuestionFromDatabaseOutput
            elif isinstance(output.get("result"), AnswerQuestionFromDatabaseOutput):
                analysis_id = output["result"].analysis_id
            else:
                analysis_id = "Unknown"
            
            # Create document title using tool name and question
            document_title = f"{tool_name}: {analysis_id}"
            
            # Format the content based on tool type
            document_data = ""
            if output.get('name') == "text_to_sql_tool" and isinstance(output.get('result'), AnswerQuestionFromDatabaseOutput):
                result = output.get('result')
                document_data += f"Question: {result.question}\n"
                document_data += f"SQL: ```sql\n{result.sql}\n```\n"
                if result.rows and result.rows != "[]":
                    document_data += f"Data: {result.rows}\n"
                if result.error:
                    document_data += f"Error: {result.error}\n"
            elif output.get('name') == "web_search_tool":
                result = output.get('result', {})
                document_data += f"Question: {output.get('input', {}).get('question', 'No question')}\n"
                document_data += f"Answer: {result.get('answer', 'No answer')}\n"
                if 'reference_sources' in result:
                    document_data += "Sources:\n"
                    for source in result.get('reference_sources', []):
                        document_data += f"- {source.get('source', 'Unknown')}: {source.get('url', 'No URL')}\n"
            elif output.get('name') == "pdf_citations_tool":
                result = output.get('result', [])
                document_data += f"Question: {output.get('input', {}).get('question', 'No question')}\n"
                document_data += f"PDF IDs: {output.get('input', {}).get('pdf_files', [])}\n"
                for item in result["citations"]:
                    if item.get('type') == 'text':
                        document_data += f"{item.get('text', '')}\n"
            
            # Add the document to the list if it has content
            if document_data:
                document_contents.append({
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": document_data
                    },
                    "title": document_title,
                    "citations": {"enabled": True},
                })
        
        # Prepare text content including Phase 1 and Phase 2 reports
        text_content = f"""I need you to synthesize all the provided analyses into a comprehensive final report that answers this original question:

{question}

{clarification_responses}

Here are the previous analysis phases to help with your synthesis:

# Phase 1: Initial Data Analysis
{analyst_response.content}

# Phase 2: Follow-up Analysis and Gap Filling
{evaluator_response.content}

Use the documents to source information with specific citations. Create a well-structured document with clear sections, highlighting key insights and supporting them with specific data points.

Your report should present the information clearly for business stakeholders, with an executive summary, logical structure, and proper formatting."""
        
        # Create content messages with citations enabled for individual tool calls
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text_content
                    },
                    # Add all individual document contents
                    *document_contents
                ]
            }
        ]
        
        # Make the API call with citations enabled
        response = await client.messages.create(
            model="claude-4-sonnet-20250514",
            messages=messages,
            system="""You are a professional report writer responsible for synthesizing extensive data analysis into a clear, insightful, and well-structured report.

Your report should:
1. Begin with a concise executive summary of key findings
2. Organize insights into logical sections with clear headings
3. Present data in a progressive narrative that builds understanding
4. Highlight the most significant findings prominently
5. Include specific data points and figures to support conclusions
6. Explain implications and connections between different insights
7. Use professional, clear language appropriate for business stakeholders
8. End with actionable conclusions or recommendations if appropriate
9. IMPORTANT: Use citations to reference specific findings from the documents

Format the report with Markdown for readability including headings, bullet points, and emphasis where appropriate.

For any mathematical expressions or formulas in your report, use LaTeX, wrapped in the following tags:
- For inline LaTeX (math within sentences), use: <latex-inline>...</latex-inline>
- For block LaTeX (displayed equations), use: <latex-block>...</latex-block>


If adding LaTeX expressions, you MUST use these specific tags exactly and consistently as shown above. This is required to properly render mathematical equations. Failure to use these tags correctly will result in LaTeX content not being properly rendered. Do NOT use `$` or `$$` conventions, they cannot be distinguished from currencies.""",
            temperature=0.3,
            max_tokens=8191,
        )
        
        LOGGER.info(f"Report response: {response}")

        # Convert response to expected format
        response_text = ""
        for item in response.content:
            if item.type == "text":
                response_text += item.text
        
        response_with_citations = [item.to_dict() for item in response.content]
        
        # Return the final output
        return GenerateReportFromQuestionOutput(
            report=response_text,
            report_with_citations=response_with_citations,
            sql_answers=all_sql_answers,
            tool_outputs=all_tool_outputs,
        )
        
    except Exception as e:
        LOGGER.error(f"Error in multi_agent_report_generation:\n{e}")
        return GenerateReportFromQuestionOutput(
            report=f"Error in multi-agent report generation: {str(e)}",
            report_with_citations=[],
            sql_answers=[],
            tool_outputs=[],
        )

