from fastapi import APIRouter, HTTPException, Request
from tools.analysis_tools import answer_question_from_database
from defog.llm.utils import chat_async

router = APIRouter()

@router.post("/answer_question_from_database")
async def answer_question_from_database_route(request: Request):
    """
    Route used for testing purposes.
    Generates SQL from a question and database.
    """
    params = await request.json()
    question = params.get("question")
    db_name = params.get("db_name")
    model = params.get("model", "o3-mini")
    try:
        tools = [answer_question_from_database]
        return await chat_async(
            model=model,
            tools=tools,
            messages=[{"role": "user", "content": f"{question} Look in the database {db_name} for your answers, and feel free to continue asking multiple questions from the database if you need to.\n\nPlease give your final answer as a descriptive report."}],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))