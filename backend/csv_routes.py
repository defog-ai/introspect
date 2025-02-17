import os
from fastapi import APIRouter, Request
from auth_utils import validate_user
from fastapi.responses import JSONResponse
from utils_sql import generate_sql_query, retry_query_after_error

router = APIRouter()


@router.post("/generate_query_csv")
async def generate_query_csv_route(request: Request):
    """
    Generates a CSV file with the results of a query
    Expects a query string
    Return a CSV file with the results of the query
    This is done by sending a POST request to the /generate_query_csv endpoint
    """
    params = await request.json()
    question = params.get("question", None)
    metadata = params.get("metadata", None)
    previous_context = params.get("previous_context", [])

    token = params.get("token", None)
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    prev_questions = []
    for item in previous_context:
        prev_question = item.get("user_question")
        if question:
            prev_steps = item.get("steps", [])
            if len(prev_steps) > 0:
                for step in prev_steps:
                    if "sql" in step:
                        prev_sql = step["sql"]
                        prev_questions.append(
                            {"question": prev_question, "sql": prev_sql}
                        )
                        break

    # metadata should be a list of dictionaries with keys 'table_name', 'column_name', 'data_type', and 'column_description'\

    if not question:
        return {"error": "no question provided"}
    if not metadata:
        return {"error": "no metadata provided"}

    resp = await generate_sql_query(
        question=question,
        metadata=metadata,
        db_type="sqlite",
        previous_context=prev_questions,
    )

    if "error" in resp and resp["error"]:
        return {
            "ran_successfully": False,
            "error": resp["error"],
        }

    else:
        return {
            "ran_successfully": True,
            "sql": resp["sql"],
            "error": resp.get("error", None),
            "previous_context": previous_context + [question, resp["sql"]],
        }


@router.post("/retry_query_csv")
async def retry_query_csv_route(request: Request):
    """
    Generates a CSV file with the results of a query
    Expects a query string
    Return a CSV file with the results of the query
    This is done by sending a POST request to the /generate_query_csv endpoint
    """
    params = await request.json()
    key_name = params.get("key_name", None)
    question = params.get("question", None)
    metadata = params.get(
        "metadata", None
    )  # metadata should be a list of dictionaries with keys 'table_name', 'column_name', 'data_type', and 'column_description'
    previous_query = params.get("previous_query", None)
    error = params.get("error", None)
    token = params.get("token", None)
    if not (await validate_user(token)):
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )

    if not key_name:
        return JSONResponse(content={"error": "no key name provided"}, status_code=400)
    if not question:
        return JSONResponse(content={"error": "no question provided"}, status_code=400)
    if not metadata:
        return JSONResponse(content={"error": "no metadata provided"}, status_code=400)
    if not previous_query:
        return JSONResponse(
            content={"error": "no previous query provided"}, status_code=400
        )
    if not error:
        return JSONResponse(content={"error": "no error provided"}, status_code=400)

    resp = await retry_query_after_error(
        question=question,
        db_type="sqlite",
        metadata=metadata,
        sql=previous_query,
        error=error,
    )

    if "error" in resp and resp["error"]:
        return JSONResponse(content={"error": resp["error"]}, status_code=400)

    return JSONResponse(
        content={
            "new_query": resp["sql"],
            "query_db": "sqlite",
            "error": resp.get("error", None),
            "status": "success",
        },
        status_code=200,
    )
