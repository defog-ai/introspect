from fastapi import APIRouter, Request
from generic_utils import (
    make_request,
    get_api_key_from_key_name,
    format_sql,
    format_date_string,
)
from auth_utils import validate_user
import os
import pandas as pd
from fastapi.responses import JSONResponse
from db_utils import get_db_type_creds

router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


@router.post("/feedback")
async def feedback(request: Request):
    """Responds to a feedback request from the user by sending the feedback to the api.defog.ai endpoint."""
    params = await request.json()
    key_name = params.get("key_name")
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    api_key = get_api_key_from_key_name(key_name)
    feedback = params.get("feedback")  # "good" or "Bad"
    text = params.get("text")  # the text of the feedback
    dev = params.get("dev")  # True or False
    response = params.get("response", {})

    if "columns" in response:
        del response["columns"]

    if "data" in response:
        del response["data"]

    if not feedback:
        feedback = "good"

    res = await send_feedback(
        {
            "api_key": api_key,
            "feedback": feedback,
            "text": text,
            "dev": dev,
            "response": response,
        },
    )
    return res


@router.post("/get_feedback")
async def get_feedback(request: Request):
    """Responds by fetching the feedback users have given in the past."""
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    url = DEFOG_BASE_URL + "/get_feedback"
    res = await make_request(url, data={"api_key": api_key})
    data = res["data"]
    for idx, item in enumerate(data):
        # first item is created_at
        data[idx][0] = format_date_string(item[0])

        # third item is the SQL query
        data[idx][3] = format_sql(item[3])

    df = pd.DataFrame(data, columns=res["columns"])
    # keep the most recent feedback for each question, query pair
    df = df.sort_values(by="created_at", ascending=False).drop_duplicates(
        subset=["question", "query_generated"]
    )
    question_id_text = (
        df[df.question_id.notnull()].set_index("question_id")["question"].to_dict()
    )
    df["parent_question_text"] = df["parent_question_id"].map(
        lambda x: (
            question_id_text.get(
                x,
                "not captured as no feedback was given for the parent question.",
            )
            if x
            else None
        )
    )
    del df["parent_question_id"]
    del df["question_id"]
    data = df.values.tolist()
    columns = df.columns.tolist()
    res["data"] = data
    res["columns"] = columns[:-1]  # remove the last column (parent_question_text)
    return res


@router.post("/get_instructions_recommendation")
async def get_instructions_recommendation(request: Request):
    """Uses negative feedback for a query to provide recommendations for instructions that might improve it."""
    params = await request.json()
    token = params.get("token")
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    question = params.get("question")
    sql_generated = params.get("sql_generated")
    user_feedback = params.get("user_feedback")
    url = DEFOG_BASE_URL + "/reflect_on_error"
    res = await get_db_type_creds(api_key)

    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    r = await make_request(
        url=url,
        data={
            "api_key": api_key,
            "question": question,
            "sql_generated": sql_generated,
            "error": user_feedback,
            "db_type": db_type,
        },
    )
    return r


### Helper functions ###


async def send_feedback(params_obj):
    """
    Sends the feedback to the api.defog.ai endpoint.

    Args:
        params_obj (dict): A dictionary containing key-value pairs representing feedback details.
            The dictionary should have the following keys:
            - 'api_key' (str): The API key for authentication.
            - 'feedback' (str): The type of feedback: 'Good' or 'Bad'.
            - 'text' (str): Feedback text provided by the user; empty if the feedback is 'Good'.
            - 'dev' (bool): Indicates if the feedback is being sent in development mode.
            - 'response' (dict): A dictionary representing the response object related to the feedback.
                This dictionary must contain the following keys:
                - 'question' (str): The question asked by the user.
                - 'questionId' (str): The unique identifier for the question.
                - 'generatedSQL' (str): The SQL query generated in response to the question.
    Returns:
        response (dict): The response object from the API request with desired "status" key with value "received".

    """
    url = DEFOG_BASE_URL + "/feedback"
    res = await make_request(url, data=params_obj)
    return res
