import os
import re
import traceback
import logging
from uuid import uuid4
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from utils_clarification import generate_clarification, classify_question_type
from utils_question_related import generate_follow_on_questions
from utils_chart import edit_chart

from agents.planner_executor.planner_executor_agent import (
    generate_assignment_understanding,
    rerun_step,
    run_step,
)

from agents.planner_executor.tool_helpers.core_functions import analyse_data_streaming

from db_analysis_utils import (
    get_analysis_data,
    get_assignment_understanding,
)
from generic_utils import make_request
from auth_utils import validate_user
from uuid import uuid4

router = APIRouter()
LOGGER = logging.getLogger("server")


@router.post("/generate_step")
async def generate_step(request: Request):
    """
    Function that returns a single step of a plan.

    Takes in previous steps generated, which defaults to an empty array.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/step-results/StepResults.jsx

    The mandatory inputs are analysis_id, a valid key_name and question.

    Note on previous_context:
    It is an array of objects. Each object references a "parent" analysis. 
    Each parent analysis has a user_question and analysis_id, steps:
     - `user_question` - contains the question asked by the user.
     - `analysis_id` - is the id of the parent analysis.
     - `steps` - are the steps generated in the parent analysis.
    """
    try:
        LOGGER.info("Generating step")
        params = await request.json()
        db_name = params.get("db_name")
        question = params.get("user_question")
        analysis_id = params.get("analysis_id")
        hard_filters = params.get("hard_filters", [])
        dev = params.get("dev", False)
        temp = params.get("temp", False)
        clarification_questions = params.get("clarification_questions", [])
        previous_context = params.get("previous_context", [])
        root_analysis_id = params.get("root_analysis_id", analysis_id)

        # if key name or question is none or blank, return error
        if not db_name or db_name == "":
            raise Exception("Invalid request. Must have DB name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

        # check if the assignment_understanding exists in the db for the root analysis (aka the original question in this thread)
        err, assignment_understanding = await get_assignment_understanding(
            analysis_id=root_analysis_id
        )

        # if assignment understanding does not exist, so try to generate it
        if assignment_understanding is None:
            _, assignment_understanding = await generate_assignment_understanding(
                analysis_id=root_analysis_id,
                clarification_questions=clarification_questions,
                db_name=db_name,
            )

        prev_questions = []
        for idx, item in enumerate(previous_context):
            for step in item["steps"]:
                prev_question = step["inputs"].get("question", "")
                if idx == 0:
                    previous_question += " (" + assignment_understanding + ")"
                prev_sql = step.get("sql")
                if prev_sql:
                    prev_questions.append({
                        "question": prev_question,
                        "sql": prev_sql
                    })
        
        # if sql_only is true, just call the sql generation function and return, while saving the step
        if type(assignment_understanding) == str and len(prev_questions) == 0:
            # remove any numbers, like "1. " from the beginning of assignment understanding
            if re.match(r"^\d+\.\s", assignment_understanding):
                assignment_understanding = re.sub(
                    r"^\d+\.\s", "", assignment_understanding
                )

            question = question + " (" + assignment_understanding + ")"
        
        inputs = {
            "question": question,
            "hard_filters": hard_filters,
            "db_name": db_name,
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
                },
                "hard_filters": {
                    "name": "hard_filters",
                    "type": "list",
                    "default": None,
                    "description": "hard filters to apply to the data",
                },
            },
        }

        analysis_execution_cache = {
            "db_name": db_name,
            "user_question": question,
            "hard_filters": hard_filters,
            "dev": dev,
            "temp": temp,
        }
        await run_step(
            analysis_id=analysis_id,
            step=step,
            analysis_execution_cache=analysis_execution_cache,
            skip_cache_storing=True,
        )
        return {
            "success": True,
            "steps": [step],
            "done": True,
        }
    except Exception as e:
        LOGGER.error(e)
        traceback.print_exc()
        return {"success": False, "error_message": str(e) or "Incorrect request"}


@router.post("/generate_follow_on_questions")
async def generate_follow_on_questions_route(request: Request):
    """
    Function that returns follow on questions for a given question.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/analysisManager.js

    The mandatory inputs are a valid key_name and question.
    """
    try:
        LOGGER.info("Generating follow on questions")
        params = await request.json()
        db_name = params.get("db_name")
        question = params.get("user_question")

        # if key name or question is none or blank, return error
        if not db_name or db_name == "":
            raise Exception("Invalid request. Must have database name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

        follow_on_questions = await generate_follow_on_questions(
            question=question, 
            db_name=db_name
        )

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
        db_name = params.get("db_name")
        question = params.get("user_question")
        previous_context = params.get("previous_context", [])
        if len(previous_context) > 1:
            return {
                "success": True,
                "done": True,
                "clarification_questions": [],
            }

        # if key name or question is none or blank, return error
        if not db_name or db_name == "":
            raise Exception("Invalid request. Must have API key name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

        clarification_questions = await generate_clarification(
            question=question,
            db_name=db_name,
        )

        if "not ambiguous" in clarification_questions.lower() or "no clarifi" in clarification_questions.lower():
            clarification_questions = []
        else:
            clarification_questions = [{"question": clarification_questions}]

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
        db_name = params.get("db_name")
        analysis_id = params.get("analysis_id")
        step_id = params.get("step_id")
        edited_step = params.get("edited_step")
        
        if not db_name or db_name == "":
            raise Exception("Invalid request. Must have API key name.")

        if not analysis_id or analysis_id == "":
            raise Exception("Invalid request. Must have analysis id.")

        if not step_id or step_id == "":
            raise Exception("Invalid request. Must have step id.")

        if not edited_step or type(edited_step) != dict:
            raise Exception("Invalid edited step given.")

        err, analysis_data = await get_analysis_data(analysis_id=analysis_id)
        if err:
            raise Exception("Error fetching analysis data from database")

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
            db_name=db_name,
            analysis_id=analysis_id,
            user_question=None,
            dev=False,
            temp=False,
        )

        return {"success": True, "steps": new_steps}
    except Exception as e:
        LOGGER.error(e)
        return {"success": False, "error_message": str(e) or "Incorrect request"}


@router.post("/edit_chart")
async def edit_chart_route(request: Request):
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

        LOGGER.info(f"Editing chart with request: {user_request}")
        
        chart_state_edits = await edit_chart(
            current_chart_state=current_chart_state,
            columns=columns,
            user_request=user_request,
        )

        if not chart_state_edits or type(chart_state_edits) != dict:
            raise Exception("Error editing chart.")

        return {"success": True, "chart_state_edits": chart_state_edits}

    except Exception as e:
        LOGGER.error("Error creating chart state: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


# setup an analysis data endpoint with streaming and websockets
@router.websocket("/analyse_data_streaming")
async def analyse_data_streaming_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data_in = await websocket.receive_json()
        question = data_in.get("question")
        data_csv = data_in.get("data_csv")
        sql = data_in.get("sql")
        async for token in analyse_data_streaming(
            question=question, data_csv=data_csv, sql=sql
        ):
            await websocket.send_text(token)
        
        # Send a final message to indicate the end of the stream
        await websocket.send_text("Defog data analysis has ended")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        LOGGER.error("Error with websocket connection:" + str(e))
        traceback.print_exc()
    finally:
        await websocket.close()

@router.post("/get_question_type")
async def get_question_type(request: Request):
    params = await request.json()
    question = params.get("question")
    token = params.get("token")
    username = await validate_user(token)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    res = await classify_question_type(question)

    return JSONResponse(
        status_code=200,
        content=res,
    )