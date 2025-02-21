import os
import re
import traceback
import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from tool_code_utilities import fetch_query_into_df
from query_data.data_fetching import data_fetcher_and_aggregator
from agent_models import AnalysisData, DataFetcherInputs, RerunRequest
from utils_sql import deduplicate_columns
from utils_clarification import (
    generate_clarification,
    classify_question_type,
    generate_assignment_understanding,
)
from utils_question_related import generate_follow_on_questions
from utils_chart import edit_chart
import pandas as pd
from db_analysis_utils import (
    get_analysis,
    get_assignment_understanding,
    initialise_analysis,
    update_analysis_data,
)
from auth_utils import validate_user_request

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Agent"],
)
LOGGER = logging.getLogger("server")


@router.post("/query-data/get_analysis")
async def get_analysis_route(request: Request):
    try:
        params = await request.json()
        analysis_id = params.get("analysis_id")

        err, analysis_data = await get_analysis(analysis_id)

        if err is not None:
            raise Exception(err)

        return JSONResponse(content=analysis_data)
    except Exception as e:
        print(e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content=str(e))


@router.post("/query-data/create_analysis")
async def create_analysis_route(request: Request):
    try:
        params = await request.json()
        token = params.get("token")
        db_name = params.get("db_name")
        initialisation_details = params.get(
            "initialisation_details",
            params.get(
                "other_data",
            ),
        )

        err, analysis = await initialise_analysis(
            user_question=initialisation_details.get("user_question"),
            token=token,
            db_name=db_name,
            custom_id=params.get("custom_id"),
            initialisation_details=initialisation_details,
        )

        LOGGER.info(analysis)

        if err is not None:
            raise Exception(err)

        return JSONResponse(content=analysis)
    except Exception as e:
        print(e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content=str(e))


@router.post("/query-data/generate_analysis")
async def generate_analysis(request: Request):
    """
    Function that returns a single step of a plan.

    Takes in previous steps generated, which defaults to an empty array.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/step-results/StepResults.jsx

    The mandatory inputs are analysis_id, a valid db_name and question.

    Note on previous_context:
    It is an array of objects. Each object references a "parent" analysis.
    Each parent analysis has a user_question and analysis_id, steps:
     - `user_question` - contains the question asked by the user.
     - `sql` - is the sql generated in the parent analysis.
    """
    try:
        LOGGER.info("Generating step")
        params = await request.json()
        db_name = params.get("db_name")
        user_question = params.get("user_question")
        analysis_id = params.get("analysis_id")
        hard_filters = params.get("hard_filters", [])
        clarification_questions = params.get("clarification_questions", [])
        previous_context = params.get("previous_context", [])
        root_analysis_id = params.get("root_analysis_id", analysis_id)

        # this will be the input to data fetcher (we will append assignment understanding to it later)
        final_question = user_question

        # if key name or question is none or blank, return error
        if not db_name or db_name == "":
            raise Exception("Invalid request. Must have DB name.")

        if not user_question or user_question == "":
            raise Exception("Invalid request. Must have a question.")

        # check if the assignment_understanding exists in the db for the root analysis (aka the original question in this thread)
        err, assignment_understanding = await get_assignment_understanding(
            analysis_id=root_analysis_id
        )

        # if assignment understanding does not exist, try to generate it
        if assignment_understanding is None:
            assignment_understanding = await generate_assignment_understanding(
                analysis_id=root_analysis_id,
                clarification_questions=clarification_questions,
                db_name=db_name,
            )

        prev_questions = []
        for idx, analysis in enumerate(previous_context):
            prev_question = analysis.get("user_question", "")
            if idx == 0 and assignment_understanding:
                prev_question += " (" + assignment_understanding + ")"
            prev_sql = analysis.get("sql")
            if prev_sql:
                prev_questions.append({"question": prev_question, "sql": prev_sql})

        # if sql_only is true, just call the sql generation function and return, while saving the step
        if type(assignment_understanding) == str and len(prev_questions) == 0:
            # remove any numbers, like "1. " from the beginning of assignment understanding
            if re.match(r"^\d+\.\s", assignment_understanding):
                assignment_understanding = re.sub(
                    r"^\d+\.\s", "", assignment_understanding
                )

            final_question = user_question + " (" + assignment_understanding + ")"

        inputs = {
            "question": final_question,
            "hard_filters": hard_filters,
            "db_name": db_name,
            "previous_context": prev_questions,
        }

        LOGGER.info(clarification_questions)

        analysis_data = AnalysisData(
            analysis_id=analysis_id,
            db_name=db_name,
            initial_question=user_question,
            tool_name="data_fetcher_and_aggregator",
            inputs=inputs,
            clarification_questions=clarification_questions,
            assignment_understanding=assignment_understanding,
            previous_context=previous_context,
        )

        err, df, sql_query = await data_fetcher_and_aggregator(**inputs)

        analysis_data.sql = None

        if err:
            analysis_data.error = err
        elif df is not None and type(df) == type(pd.DataFrame()):
            analysis_data.sql = sql_query

            # process the output
            deduplicated = deduplicate_columns(df)

            analysis_data.output = deduplicated.to_csv(float_format="%.3f", index=False)

        err, updated_analysis = await update_analysis_data(
            analysis_id=analysis_id,
            new_data=analysis_data,
        )

        return JSONResponse(content=updated_analysis)
    except Exception as e:
        LOGGER.error(e)
        traceback.print_exc()
        return JSONResponse(
            status_code=400,
            content=str(e) or "Incorrect request",
        )


@router.post("/query-data/generate_follow_on_questions")
async def generate_follow_on_questions_route(request: Request):
    """
    Function that returns follow on questions for a given question.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/analysisManager.js

    The mandatory inputs are a valid db_name and question.
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
            question=question, db_name=db_name
        )

        return {
            "success": True,
            "done": True,
            "follow_on_questions": follow_on_questions,
        }

    except Exception as e:
        LOGGER.error(e)
        return {"success": False, "error_message": str(e) or "Incorrect request"}


@router.post("/query-data/clarify")
async def clarify(request: Request):
    """
    Function that returns clarifying questions, if any, for a given question.

    If analysis id is passed, it also stores the clarifying questions in the analysis data.

    This is called by the front end's lib/components/agent/analysis/analysisManager.js from inside the `submit` function.

    Rendered by lib/components/agent/analysis/Clarify.jsx

    The mandatory inputs are a valid db_name and question.
    """
    try:
        LOGGER.info("Generating clarification questions")
        params = await request.json()
        db_name = params.get("db_name")
        question = params.get("user_question")
        analysis_id = params.get("analysis_id")

        previous_context = params.get("previous_context", [])
        # if key name or question is none or blank, return error
        if not db_name or db_name == "":
            raise Exception("Invalid request. Must have API key name.")

        if not question or question == "":
            raise Exception("Invalid request. Must have a question.")

        if len(previous_context) <= 1:
            clarification_questions = await generate_clarification(
                question=question,
                db_name=db_name,
            )
            if (
                "not ambiguous" in clarification_questions.lower()
                or "no clarifi" in clarification_questions.lower()
            ):
                clarification_questions = []
            else:
                clarification_questions = [{"question": clarification_questions}]

        LOGGER.info(clarification_questions)
        analysis_data = AnalysisData(
            analysis_id=analysis_id,
            db_name=db_name,
            initial_question=question,
            clarification_questions=clarification_questions,
            previous_context=previous_context,
        )

        err, updated_analysis = await update_analysis_data(
            analysis_id=analysis_id,
            new_data=analysis_data,
        )

        return JSONResponse(content=updated_analysis)
    except Exception as e:
        LOGGER.error(e)
        return {"success": False, "error_message": str(e) or "Incorrect request"}


@router.post("/query-data/rerun")
async def rerun_endpoint(request: RerunRequest):
    """
    Function that re runs a step given:
    1. Analysis ID
    3. edited_inputs: new inputs
    """
    LOGGER.info("Rerunning analysis")
    analysis_id = request.analysis_id
    edited_inputs = request.edited_inputs
    db_name = request.db_name

    try:
        LOGGER.info(edited_inputs.model_dump())

        err, analysis = await get_analysis(analysis_id)

        if err:
            raise Exception(err)

        if analysis.get("data") is None or analysis["data"].get("inputs") is None:
            raise Exception("Analysis has no data")

        did_question_change = False
        if edited_inputs.question:
            LOGGER.info(analysis["data"]["inputs"]["question"])
            LOGGER.info(edited_inputs.question)
            if analysis["data"]["inputs"]["question"] != edited_inputs.question:
                did_question_change = True

        old_question = analysis["data"]["inputs"]["question"]
        new_inputs = DataFetcherInputs(
            question=old_question,
            db_name=db_name,
            previous_context=analysis["data"]["inputs"].get("previous_context") or [],
            hard_filters=edited_inputs.hard_filters
            or analysis["data"]["inputs"].get("hard_filters")
            or [],
        )

        # we have to rerun everything with the new inputs
        analysis_data = AnalysisData(**analysis["data"])

        if did_question_change:
            LOGGER.info("Question changed, rerunning from scratch")
            new_inputs.question = edited_inputs.question
            err, df, sql_query = await data_fetcher_and_aggregator(**new_inputs)

            analysis_data.sql = None

            if err:
                analysis_data.error = err
            elif df is not None and type(df) == type(pd.DataFrame()):
                analysis_data.sql = sql_query

                # process the output
                deduplicated = deduplicate_columns(df)

                analysis_data.output = deduplicated.to_csv(
                    float_format="%.3f", index=False
                )
        elif edited_inputs.sql:
            LOGGER.info("Question unchanged, rerunning the sql")
            new_query = edited_inputs.sql

            try:
                df, sql_query = await fetch_query_into_df(
                    db_name=db_name,
                    sql_query=new_query,
                    question=old_question,
                )

                analysis_data.sql = sql_query

                # process the output
                deduplicated = deduplicate_columns(df)

                analysis_data.output = deduplicated.to_csv(
                    float_format="%.3f", index=False
                )
            except Exception as e:
                analysis_data.error = str(e)

        err, updated_analysis = await update_analysis_data(
            analysis_id=analysis_id,
            new_data=analysis_data,
        )

        if err:
            raise Exception(err)

        return JSONResponse(content=updated_analysis)
    except Exception as e:
        LOGGER.error(e)
        return JSONResponse(status_code=500, content=str(e))


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


@router.post("/get_question_type")
async def get_question_type_route(request: Request):
    params = await request.json()
    question = params.get("question")
    res = await classify_question_type(question)

    return JSONResponse(
        status_code=200,
        content=res,
    )
