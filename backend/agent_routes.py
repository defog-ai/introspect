import traceback
from uuid import uuid4
from fastapi import APIRouter, Request
from agents.clarifier.clarifier_agent import get_clarification

from agents.planner_executor.planner_executor_agent import (
    generate_assignment_understanding,
    generate_single_step,
    rerun_step,
    run_step,
)
import logging

logging.basicConfig(level=logging.INFO)

from db_utils import (
    get_all_tools,
    get_analysis_data,
    get_assignment_understanding,
    update_analysis_data,
)
from generic_utils import get_api_key_from_key_name, make_request
from uuid import uuid4

router = APIRouter()

import os

import redis

REDIS_HOST = os.getenv("REDIS_INTERNAL_HOST", "agents-redis")
REDIS_PORT = os.getenv("REDIS_INTERNAL_PORT", 6379)
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
)

redis_available = False
question_cache = {}
try:
    # check if redis is available
    redis_client.ping()
    redis_available = True
except Exception as e:
    logging.error(f"Error connecting to redis. Using in-memory cache instead.")


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
        logging.info("Generating step")
        params = await request.json()
        key_name = params.get("key_name")
        question = params.get("user_question")
        analysis_id = params.get("analysis_id")
        dev = params.get("dev", False)
        temp = params.get("temp", False)
        clarification_questions = params.get("clarification_questions", [])
        toolboxes = params.get("toolboxes", [])
        sql_only = params.get("sql_only", False)
        previous_questions = params.get("previous_questions", [])

        if len(previous_questions) > 0:
            previous_questions = previous_questions[:-1]

        prev_questions = []
        for item in previous_questions:
            prev_question = item.get("user_question")
            if question:
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

        # if key name or question is none or blank, return error
        if not key_name or key_name == "":
            raise Exception("Invalid request. Must have API key name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

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

        if sql_only:
            # if sql_only is true, just call the sql generation function and return, while saving the step
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
                "toolboxes": toolboxes,
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
            if len(prev_questions) > 0:
                # make a request to combine the previous questions and the current question

                if (
                    redis_client.exists(f"unified_question:{analysis_id}")
                    or analysis_id in question_cache
                ):
                    if redis_available:
                        question = redis_client.get(f"unified_question:{analysis_id}")
                    else:
                        question = question_cache.get(analysis_id)
                else:
                    question_unifier_url = (
                        os.getenv("DEFOG_BASE_URL", "https://api.defog.ai")
                        + "/convert_question_to_single"
                    )
                    unified_question = await make_request(
                        url=question_unifier_url,
                        json={
                            "api_key": api_key,
                            "question": question,
                            "previous_context": prev_questions,
                        },
                    )
                    question = unified_question.get("rephrased_question", question)
                    if redis_available:
                        redis_client.setex(
                            f"unified_question:{analysis_id}", 3600, question
                        )
                    else:
                        question_cache[analysis_id] = question

                print(f"*******\nUnified question: {question}\n********", flush=True)

            step = await generate_single_step(
                dfg_api_key=api_key,
                analysis_id=analysis_id,
                user_question=question,
                dev=dev,
                temp=temp,
                toolboxes=toolboxes,
                assignment_understanding=assignment_understanding,
            )

            return {
                "success": True,
                "steps": [step],
                "done": step.get("done", True),
            }

    except Exception as e:
        logging.error(e)
        traceback.print_exc()
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
        logging.info("Generating clarification questions")
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

        err = await generate_assignment_understanding(
            analysis_id=analysis_id,
            clarification_questions=clarification_questions,
            dfg_api_key=api_key,
        )

        if err:
            raise Exception("Error generating assignment understanding")

        return {
            "success": True,
            "done": True,
            "clarification_questions": clarification_questions,
        }

    except Exception as e:
        logging.error(e)
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
        toolboxes = params.get("toolboxes", [])

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
            toolboxes=toolboxes,
            dev=False,
            temp=False,
        )

        return {"success": True, "steps": new_steps}
    except Exception as e:
        logging.error(e)
        return {"success": False, "error_message": str(e) or "Incorrect request"}


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

        # # # update analysis data
        update_err = await update_analysis_data(
            analysis_id, "gen_steps", new_steps, replace=True
        )

        if update_err:
            return {"success": False, "error_message": update_err}

        return {"success": True, "new_steps": new_steps}

    except Exception as e:
        logging.error("Error deleting steps: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


@router.post("/create_new_step")
async def create_new_step(request: Request):
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
            return {
                "success": False,
                "error_message": "Outputs provided are either blank or incorrect.",
            }

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
            toolboxes=[],
            dev=False,
            temp=False,
        )

        return {"success": True, "new_steps": new_steps}

    except Exception as e:
        logging.error("Error creating new step: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}
