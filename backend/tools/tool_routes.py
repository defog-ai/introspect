from auth_utils import validate_user_request
from fastapi import APIRouter, Depends
from llm_api import ALL_MODELS, O3_MINI
from request_models import (
    AnswerQuestionFromDatabaseRequest,
    SynthesizeReportFromQuestionRequest,
)
from tools.analysis_models import GenerateReportFromQuestionInput
from tools.analysis_tools import (
    generate_report_from_question,
    synthesize_report_from_questions,
)

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
)


@router.post("/answer_question_from_database")
async def answer_question_from_database_route(
    request: AnswerQuestionFromDatabaseRequest,
):
    """
    Route used for testing purposes.
    Generates SQL from a question and database.
    """
    question = request.question
    db_name = request.db_name
    model = request.model if request.model and request.model in ALL_MODELS else O3_MINI
    return await generate_report_from_question(
        GenerateReportFromQuestionInput(
            question=question,
            db_name=db_name,
            model=model,
        )
    )


@router.post("/synthesize_report_from_question")
async def synthesize_report_from_question_route(
    request: SynthesizeReportFromQuestionRequest,
):
    """
    Synthesizes a report from a question.
    Multiple reports are generated and synthesized into a final report.
    """
    model = request.model if request.model and request.model in ALL_MODELS else O3_MINI
    return await synthesize_report_from_questions(
        GenerateReportFromQuestionInput(
            question=request.question,
            db_name=request.db_name,
            model=model,
            num_reports=request.num_reports,
        )
    )
