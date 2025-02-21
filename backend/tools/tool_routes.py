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
            messages=[
                {
                    "role": "developer",
                    "content": "Formatting re-enabled"
                },
                {
                    "role": "user",
                    "content": f"""{question} Look in the database {db_name} for your answers, and feel free to continue asking multiple questions from the database if you need to. I would rather that you ask a lot of questions than too few.

Try to aggregate data in clear and understandable buckets.

Please give your final answer as a descriptive report.

For each point that you make in the report, please include the relevant SQL query that was used to generate the data for it. You can include as many SQL queries as you want, including multiple SQL queries for one point.
"""
}],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))