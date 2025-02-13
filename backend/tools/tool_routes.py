from fastapi import APIRouter, Request, HTTPException

from analysis_models import AnswerQuestionFromDatabaseInput, AnswerQuestionFromDatabaseOutput
from analysis_tools import answer_question_from_database

router = APIRouter()

@router.post("/answer_question_from_database")
async def answer_question_from_database_route(
    input: AnswerQuestionFromDatabaseInput
) -> AnswerQuestionFromDatabaseOutput:
    try:
        output = await answer_question_from_database(input)
        return AnswerQuestionFromDatabaseOutput(**output.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))