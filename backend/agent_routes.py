import traceback
from uuid import uuid4
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from agents.clarifier.clarifier_agent import get_clarification

import pandas as pd

from agents.planner_executor.planner_executor_agent import (
    generate_assignment_understanding,
    generate_single_step,
    rerun_step,
    run_step,
)
import logging

LOGGER = logging.getLogger("server")

from agents.planner_executor.tool_helpers.get_tool_library_prompt import (
    get_tool_library_prompt,
)
from utils import snake_case
from db_utils import (
    add_tool,
    check_tool_exists,
    delete_tool,
    get_all_tools,
    get_analysis_data,
    get_assignment_understanding,
    update_analysis_data,
)
from generic_utils import get_api_key_from_key_name, make_request
from uuid import uuid4

router = APIRouter()

import os
import re
import redis

REDIS_HOST = os.getenv("REDIS_INTERNAL_HOST", "agents-redis")
REDIS_PORT = os.getenv("REDIS_INTERNAL_PORT", 6379)
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)

llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")

redis_available = False
question_cache = {}
try:
    # check if redis is available
    redis_client.ping()
    redis_available = True
except Exception as e:
    LOGGER.error(f"Error connecting to redis. Using in-memory cache instead.")


@router.post("/generate_step")
async def generate_step(request: Request):
    """
    Function that returns a single step of a plan.

    Takes in previous steps generated, which defaults to an empty array.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/step-results/StepResults.jsx

    The mandatory inputs are analysis_id, a valid key_name and question.
    """
    try:
        LOGGER.info("Generating step")
        params = await request.json()
        key_name = params.get("key_name")
        question = params.get("user_question")
        analysis_id = params.get("analysis_id")
        dev = params.get("dev", False)
        temp = params.get("temp", False)
        clarification_questions = params.get("clarification_questions", [])
        sql_only = params.get("sql_only", False)
        previous_questions = params.get("previous_questions", [])
        extra_tools = params.get("extra_tools", [])
        planner_question_suffix = params.get("planner_question_suffix", None)

        if len(previous_questions) > 0:
            previous_questions = previous_questions[:-1]

        # if key name or question is none or blank, return error
        if not key_name or key_name == "":
            raise Exception("Invalid request. Must have API key name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

        prev_questions = []
        for item in previous_questions:
            prev_question = item.get("user_question")
            prev_steps = (
                item.get("analysisManager", {})
                .get("analysisData", {})
                .get("gen_steps", {})
                .get("steps", [])
            )
            if len(prev_steps) > 0:
                for step in prev_steps:
                    if "sql" in step:
                        prev_sql = step["sql"]
                        prev_questions.append(prev_question)
                        prev_questions.append(prev_sql)
                        break

        api_key = get_api_key_from_key_name(key_name)

        if not api_key:
            raise Exception("Invalid API key name.")

        if len(clarification_questions) > 0:
            # this means that the user has answered the clarification questions
            # so we can generate the assignment understanding (which is just a statement of the user's clarifications)

            # check if the assignment_understanding exists in the db for this analysis_id
            err, assignment_understanding = get_assignment_understanding(
                analysis_id=analysis_id
            )

            # if it doesn't exist, then `assignment_understanding` will be None
            if assignment_understanding is None:
                _, assignment_understanding = await generate_assignment_understanding(
                    analysis_id=analysis_id,
                    clarification_questions=clarification_questions,
                    dfg_api_key=api_key,
                )
        else:
            assignment_understanding = None

        # unify questions if there are previous questions
        if len(prev_questions) > 0:
            # make a request to combine the previous questions and the current question

            question_unifier_url = (
                os.getenv("DEFOG_BASE_URL", "https://api.defog.ai")
                + "/convert_question_to_single"
            )
            unified_question = await make_request(
                url=question_unifier_url,
                data={
                    "api_key": api_key,
                    "question": question,
                    "previous_context": prev_questions,
                },
            )
            question = unified_question.get("rephrased_question", question)
            print(question)
            print(f"*******\nUnified question: {question}\n********", flush=True)

        if sql_only:
            # if sql_only is true, just call the sql generation function and return, while saving the step
            if type(assignment_understanding) == str:
                # remove any numbers, like "1. " from the beginning of assignment understanding
                if re.match(r"^\d+\.\s", assignment_understanding):
                    assignment_understanding = re.sub(
                        r"^\d+\.\s", "", assignment_understanding
                    )

                question = question + " (" + assignment_understanding + ")"
                print(
                    f"*******\nQuestion with assignment understanding:\n{question}\n*******",
                    flush=True,
                )
            inputs = {
                "question": question,
                "global_dict": {
                    "dfg_api_key": api_key,
                    "dev": dev,
                    "temp": temp,
                },
                "previous_context": prev_questions,
            }

            step_id = str(uuid4())
            step = {
                "description": question,
                "tool_name": "data_fetcher_and_aggregator",
                "inputs": inputs,
                "outputs_storage_keys": ["answer"],
                "done": True,
                "id": step_id,
                "error_message": None,
                "input_metadata": {
                    "question": {
                        "name": "question",
                        "type": "str",
                        "default": None,
                        "description": "natural language description of the data required to answer this question (or get the required information for subsequent steps) as a string",
                    }
                },
            }

            analysis_execution_cache = {
                "dfg_api_key": api_key,
                "user_question": question,
                "dev": dev,
                "temp": temp,
            }
            await run_step(
                analysis_id=analysis_id,
                step=step,
                all_steps=[step],
                analysis_execution_cache=analysis_execution_cache,
                skip_cache_storing=True,
                resolve_inputs=False,
            )
            return {
                "success": True,
                "steps": [step],
                "done": True,
            }

        else:
            question = question.strip()
            # make sure the extra tools don't already exist in the db
            for tool in extra_tools:
                tool_name = tool.get("tool_name", "")
                err, exists, existing_tool = await check_tool_exists(tool_name)
                if err or exists:
                    raise Exception(f"Tool with name {tool_name} already exists.")

            # if we're here, add the extra tools to the db
            for tool in extra_tools:
                err = await add_tool(
                    api_key=api_key,
                    tool_name=tool.get("tool_name", ""),
                    function_name=tool.get("function_name", ""),
                    description=tool.get("description", ""),
                    code=tool.get("code", ""),
                    input_metadata=tool.get("input_metadata", {}),
                    output_metadata=tool.get("output_metadata", []),
                )
                if err:
                    raise Exception(err)

            step = await generate_single_step(
                dfg_api_key=api_key,
                analysis_id=analysis_id,
                user_question=question
                + (
                    f"Note: {planner_question_suffix}"
                    if planner_question_suffix
                    else ""
                ),
                dev=dev,
                temp=temp,
                assignment_understanding=assignment_understanding,
            )

            return {
                "success": True,
                "steps": [step],
                "done": step.get("done", True),
            }

    except Exception as e:
        LOGGER.error(e)
        traceback.print_exc()
        return {"success": False, "error_message": str(e) or "Incorrect request"}
    finally:
        # remove extra tools from the db
        for tool in extra_tools:
            function_name = tool.get("function_name", "")
            # deletion happens using function name, not tool name
            err = await delete_tool(function_name)
            if err:
                LOGGER.error(f"Error deleting tool {function_name}: {err}")


@router.post("/generate_follow_on_questions")
async def generate_follow_on_questions(request: Request):
    """
    Function that returns follow on questions for a given question.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/analysisManager.js

    The mandatory inputs are a valid key_name and question.
    """
    try:
        LOGGER.info("Generating follow on questions")
        params = await request.json()
        key_name = params.get("key_name")
        question = params.get("user_question")

        # if key name or question is none or blank, return error
        if not key_name or key_name == "":
            raise Exception("Invalid request. Must have API key name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

        api_key = get_api_key_from_key_name(key_name)

        if not api_key:
            raise Exception("Invalid API key name.")

        follow_on_questions = await make_request(
            url=os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
            + "/generate_follow_on_questions",
            data={
                "api_key": api_key,
                "question": question,
            },
        )
        if follow_on_questions:
            follow_on_questions = follow_on_questions.get("follow_on_questions", [])
        else:
            follow_on_questions = []

        return {
            "success": True,
            "done": True,
            "follow_on_questions": follow_on_questions,
        }

    except Exception as e:
        LOGGER.error(e)
        return {"success": False, "error_message": str(e) or "Incorrect request"}


@router.post("/clarify")
async def clarify(request: Request):
    """
    Function that returns clarifying questions, if any, for a given question.

    If analysis id is passed, it also stores the clarifying questions in the analysis data.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/Clarify.jsx

    The mandatory inputs are a valid key_name and question.
    """
    try:
        LOGGER.info("Generating clarification questions")
        params = await request.json()
        key_name = params.get("key_name")
        question = params.get("user_question")
        analysis_id = params.get("analysis_id")

        # if key name or question is none or blank, return error
        if not key_name or key_name == "":
            raise Exception("Invalid request. Must have API key name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

        api_key = get_api_key_from_key_name(key_name)

        if not api_key:
            raise Exception("Invalid API key name.")

        dev = params.get("dev", False)
        temp = params.get("temp", False)

        clarification_questions = await get_clarification(
            question=question,
            api_key=api_key,
            dev=dev,
            temp=temp,
        )

        return {
            "success": True,
            "done": True,
            "clarification_questions": clarification_questions,
        }

    except Exception as e:
        LOGGER.error(e)
        return {"success": False, "error_message": str(e) or "Incorrect request"}


@router.post("/rerun_step")
async def rerun_step_endpoint(request: Request):
    """
    Function that re runs a step given:
    1. Analysis ID
    2. Step id to re run
    3. The edited step
    4. Clarification questions

    Note that it will only accept edits to one step. If the other steps have been edited, but they have not been re run, they will be re run with the original inputs (because unless the user presses re run on the front end, we don't get their edits).

    It re runs both the parents and the dependent steps of the step to re run.

    Called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `reRun` function.
    """
    try:
        params = await request.json()
        key_name = params.get("key_name")
        analysis_id = params.get("analysis_id")
        step_id = params.get("step_id")
        edited_step = params.get("edited_step")
        extra_tools = params.get("extra_tools", [])
        planner_question_suffix = params.get("planner_question_suffix", None)

        if not key_name or key_name == "":
            raise Exception("Invalid request. Must have API key name.")

        api_key = get_api_key_from_key_name(key_name)

        if not api_key:
            raise Exception("Invalid API key name.")

        if not analysis_id or analysis_id == "":
            raise Exception("Invalid request. Must have analysis id.")

        if not step_id or step_id == "":
            raise Exception("Invalid request. Must have step id.")

        if not edited_step or type(edited_step) != dict:
            raise Exception("Invalid edited step given.")

        err, analysis_data = get_analysis_data(analysis_id=analysis_id)
        if err:
            raise Exception("Error fetching analysis data from database")

        # make sure the extra tools don't already exist in the db
        for tool in extra_tools:
            tool_name = tool.get("tool_name", "")
            err, exists, existing_tool = await check_tool_exists(tool_name)
            if err or exists:
                raise Exception(f"Tool with name {tool_name} already exists.")

        # if we're here, add the extra tools to the db
        for tool in extra_tools:
            err = await add_tool(
                api_key=api_key,
                tool_name=tool.get("tool_name", ""),
                function_name=tool.get("function_name", ""),
                description=tool.get("description", ""),
                code=tool.get("code", ""),
                input_metadata=tool.get("input_metadata", {}),
                output_metadata=tool.get("output_metadata", []),
            )
            if err:
                raise Exception(err)

        # we use the original versions of all steps but the one being rerun
        all_steps = analysis_data.get("gen_steps", {}).get("steps", [])

        # first make sure the step exists in all_steps
        step_idx = None
        for i, s in enumerate(all_steps):
            if s.get("id") == step_id:
                all_steps[i] = edited_step
                step_idx = i
                break

        if step_idx is None:
            raise Exception("Step not found in all steps.")

        # rerun this step and all its parents and dependents
        # the re run function will handle the storage of all the steps in the db
        new_steps = await rerun_step(
            step=all_steps[step_idx],
            all_steps=all_steps,
            analysis_id=analysis_id,
            dfg_api_key=api_key,
            user_question=None,
            dev=False,
            temp=False,
        )

        return {"success": True, "steps": new_steps}
    except Exception as e:
        LOGGER.error(e)
        return {"success": False, "error_message": str(e) or "Incorrect request"}
    finally:
        # remove extra tools from the db
        for tool in extra_tools:
            function_name = tool.get("function_name", "")
            # deletion happens using function name, not tool name
            err = await delete_tool(function_name)
            if err:
                LOGGER.error(f"Error deleting tool {function_name}: {err}")


@router.post("/delete_steps")
async def delete_steps(request: Request):
    """
    Delete steps from an analysis using the anlaysis_id and step ids passed.

    Returns new steps after deletion.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `deleteStepsWrapper` function.
    """
    try:
        data = await request.json()
        step_ids = data.get("step_ids")
        analysis_id = data.get("analysis_id")

        if step_ids is None or type(step_ids) != list:
            raise Exception("Invalid step ids.")

        if analysis_id is None or type(analysis_id) != str:
            raise Exception("Invalid analysis id.")

        # try to get this analysis' data
        err, analysis_data = get_analysis_data(analysis_id)
        if err:
            raise Exception("Error fetching analysis data from database")

        # get the steps
        steps = analysis_data.get("gen_steps", {})
        if steps and steps["success"]:
            steps = steps["steps"]
        else:
            raise Exception("No steps found for analysis")

        # remove the steps with these tool run ids
        new_steps = [s for s in steps if s["id"] not in step_ids]

        # update analysis data
        update_err = await update_analysis_data(
            analysis_id, "gen_steps", new_steps, replace=True
        )

        if update_err:
            return {"success": False, "error_message": update_err}

        return {"success": True, "new_steps": new_steps}

    except Exception as e:
        LOGGER.error("Error deleting steps: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


@router.post("/manually_create_new_step")
async def manually_create_new_step(request: Request):
    """
    This is called when a user adds a step on the front end.

    This will receive a tool name, and tool inputs.

    This will create a new step in the analysis.

    Then it will run the new step and all its dependents/parents.

    Returns the new steps after addition.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `createNewStep` function.

    The UI components for this are in lib/components/agent/analysis/agent/add-step/*.
    """
    try:
        data = await request.json()
        # check if this has analysis_id, tool_name and inputs
        analysis_id = data.get("analysis_id")
        tool_name = data.get("tool_name")
        inputs = data.get("inputs")
        outputs_storage_keys = data.get("outputs_storage_keys")
        key_name = data.get("key_name")
        extra_tools = data.get("extra_tools", [])
        planner_question_suffix = data.get("planner_question_suffix", None)

        if not key_name or key_name == "":
            raise Exception("Invalid request. Must have API key name.")

        api_key = get_api_key_from_key_name(key_name)

        if not api_key:
            raise Exception("Invalid API key name.")

        err, tools = get_all_tools()

        if err:
            raise Exception(err)

        if analysis_id is None or type(analysis_id) != str:
            raise Exception("Invalid analysis id.")

        if tool_name is None or type(tool_name) != str or tool_name not in tools:
            raise Exception("Invalid tool name.")

        if inputs is None or type(inputs) != dict:
            raise Exception("Invalid inputs.")

        if outputs_storage_keys is None or type(outputs_storage_keys) != list:
            raise Exception("Invalid outputs provided.")

        if len(outputs_storage_keys) == 0:
            raise Exception("Please type in output names.")

        # if any of the outputs are empty or aren't strings
        if any([not o or type(o) != str for o in outputs_storage_keys]):
            raise Exception("Outputs provided are either blank or incorrect.")

        # make sure the extra tools don't already exist in the db
        for tool in extra_tools:
            tool_name = tool.get("tool_name", "")
            err, exists, existing_tool = await check_tool_exists(tool_name)
            if err or exists:
                raise Exception(f"Tool with name {tool_name} already exists.")

        # if we're here, add the extra tools to the db
        for tool in extra_tools:
            err = await add_tool(
                api_key=api_key,
                tool_name=tool.get("tool_name", ""),
                function_name=tool.get("function_name", ""),
                description=tool.get("description", ""),
                code=tool.get("code", ""),
                input_metadata=tool.get("input_metadata", {}),
                output_metadata=tool.get("output_metadata", []),
            )
            if err:
                raise Exception(err)

        # a new empty step
        new_step = {
            "tool_name": tool_name,
            "inputs": inputs,
            "id": str(uuid4()),
            "outputs_storage_keys": outputs_storage_keys,
        }

        # update analysis data with the new empty step
        update_err = await update_analysis_data(analysis_id, "gen_steps", [new_step])

        if update_err:
            raise Exception(update_err)

        # now try to get this analysis' data (this will include the new step added)
        err, analysis_data = get_analysis_data(analysis_id)
        if err:
            raise Exception(err)

        # get the steps
        all_steps = analysis_data.get("gen_steps")
        if all_steps and all_steps["success"]:
            all_steps = all_steps["steps"]
        else:
            raise Exception("No steps found for analysis")

        new_steps = await rerun_step(
            step=new_step,
            all_steps=all_steps,
            dfg_api_key=api_key,
            analysis_id=analysis_id,
            user_question=None,
            dev=False,
            temp=False,
        )

        return {"success": True, "new_steps": new_steps}

    except Exception as e:
        LOGGER.error("Error creating new step: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}
    finally:
        # remove extra tools from the db
        for tool in extra_tools:
            function_name = tool.get("function_name", "")
            # deletion happens using function name, not tool name
            err = await delete_tool(function_name)
            if err:
                LOGGER.error(f"Error deleting tool {function_name}: {err}")


@router.post("/edit_chart")
async def edit_chart(request: Request):
    """
    This is called when a user wants to edit a chart, via the search bar in the chart container.

    Sends a request to the backend with the current chart state, user's request, and the columns in the data.
    """
    try:
        data = await request.json()
        # what the user wants to change in the chart
        user_request = data.get("user_request")
        # the columns in the data
        columns = data.get("columns")
        current_chart_state = data.get("current_chart_state")

        # verify column structure
        if columns is None or type(columns) != list:
            raise Exception("Invalid columns provided.")

        if len(columns) == 0:
            raise Exception("Please provide columns.")

        if not user_request or user_request == "":
            raise Exception("Invalid user request provided.")

        if current_chart_state is None or type(current_chart_state) != dict:
            raise Exception("Invalid chart state provided.")

        # send this to the main defog python backend
        edit_chart_url = (
            os.getenv("DEFOG_BASE_URL", "https://api.defog.ai") + "/edit_chart"
        )

        LOGGER.info(f"Editing chart with request: {user_request}")
        LOGGER.info(f"Columns: {columns}")
        LOGGER.info(f"Current chart state: {current_chart_state}")

        res = await make_request(
            url=edit_chart_url,
            data={
                "user_request": user_request,
                "columns": [
                    {"title": c["title"], "col_type": c["col_type"]} for c in columns
                ],
                "current_chart_state": current_chart_state,
            },
        )
        chart_state_edits = res["chart_state_edits"]

        if not chart_state_edits or type(chart_state_edits) != dict:
            raise Exception("Error editing chart.")

        return {"success": True, "chart_state_edits": chart_state_edits}

    except Exception as e:
        LOGGER.error("Error creating chart state: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


@router.post("/generate_or_edit_tool_code")
async def generate_or_edit_tool_code(request: Request):
    """
    This function/endpoint does two things:
    1. Generates a new tool or tweaks an existing tool based on some user question.
    2. The endpoint that generates the tool on the api, will also return a sample question based on the user's tool library and ddl. This sample question will then be used to create a new plan using this tool.

    The first step above can have two modes:
    1. Generate a new tool based on either based on a tool name and description.
    2. Or given already existing tool code (`current_code` parameter), will tweak the tool code according to the `user_question` parameter, which contains the user's request for what tweak has to be made.
    """
    try:
        data = await request.json()
        tool_name = data.get("tool_name")
        tool_description = data.get("tool_description")
        user_question = data.get("user_question")
        current_code = data.get("current_code")
        key_name = data.get("key_name")
        api_key = get_api_key_from_key_name(key_name)

        LOGGER.info(f"KEY NAME: {key_name}, API KEY: {api_key}")

        if not tool_name:
            raise Exception("Invalid parameters.")

        if not user_question or user_question == "":
            user_question = "Please write the tool code."

        # if a tool with this tool name already exists, return an error
        err, exists, existing_tool = await check_tool_exists(tool_name)
        if exists:
            raise Exception(f"Tool with name {tool_name} already exists.")

        payload = {
            "request_type": "generate_or_edit_tool_code",
            "tool_name": tool_name,
            "tool_description": tool_description,
            "user_question": user_question,
            "current_code": current_code,
            "tool_library_prompt": await get_tool_library_prompt(),
            "api_key": api_key,
        }

        retries = 0
        error = None
        messages = None
        while retries < 3:
            try:
                resp = await make_request(
                    llm_calls_url,
                    payload,
                )

                if resp.get("error_message"):
                    raise Exception(resp.get("error_message"))

                tool_code = resp["tool_code"]
                messages = resp["messages"]
                input_metadata = resp["input_metadata"]
                output_metadata = resp["output_metadata"]

                # find the function name in tool_code
                try:
                    function_name = tool_code.split("def ")[1].split("(")[0]
                except Exception as e:
                    LOGGER.error("Error finding function name: " + str(e))
                    # default to snake case tool name
                    function_name = snake_case(tool_name)
                    LOGGER.error("Defaulting to snake case tool name: " + function_name)

                return JSONResponse(
                    {
                        "success": True,
                        "tool_name": tool_name,
                        "tool_description": tool_description,
                        "generated_code": tool_code,
                        "function_name": function_name,
                        "input_metadata": input_metadata,
                        "output_metadata": output_metadata,
                    }
                )
            except Exception as e:
                error = str(e)[:300]
                LOGGER.info("Error generating tool code: " + str(e))
                traceback.print_exc()
            finally:
                if error:
                    payload = {
                        "request_type": "fix_tool_code",
                        "error": error,
                        "messages": messages,
                        "api_key": api_key,
                    }
                retries += 1

        LOGGER.info("Max retries reached but couldn't generate code.")
        raise Exception("Max retries exceeded but couldn't generate code.")

    except Exception as e:
        LOGGER.info("Error generating tool code: " + str(e))
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Unable to generate tool code: " + str(e)[:300],
        }
