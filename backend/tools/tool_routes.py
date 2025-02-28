from auth_utils import validate_user_request
from fastapi import APIRouter, Depends
from request_models import (
    AnswerQuestionFromDatabaseRequest,
    SynthesizeReportFromQuestionRequest,
    WebSearchRequest,
)
from tools.analysis_models import (
    GenerateReportFromQuestionInput,
    AnswerQuestionViaGoogleSearchInput,
)
from tools.analysis_tools import (
    generate_report_from_question,
    synthesize_report_from_questions,
    web_search_tool,
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
    model = request.model or "o3-mini"
    return await generate_report_from_question(
        question=question,
        db_name=db_name,
        model=model,
        clarification_responses="",
        post_tool_func=None
    )


@router.post("/synthesize_report_from_question")
async def synthesize_report_from_question_route(
    request: SynthesizeReportFromQuestionRequest,
):
    """
    Synthesizes a report from a question.
    Multiple reports are generated and synthesized into a final report.
    """
    model = request.model if request.model else "o3-mini"
    return await synthesize_report_from_questions(
        GenerateReportFromQuestionInput(
            question=request.question,
            db_name=request.db_name,
            model=model,
            num_reports=request.num_reports,
        )
    )


@router.post("/web_search")
async def web_search_route(request: WebSearchRequest):
    """
    Test route for testing the web search tool.
    Performs a Google search for the given question and returns the AI-generated
    summary of the search results.
    """
    try:
        search_input = AnswerQuestionViaGoogleSearchInput(
            question=request.question,
        )
        search_result = await web_search_tool(search_input)
        
        # Return a structured response
        return {
            "question": request.question,
            "search_result": search_result
        }
    except Exception as e:
        # Return error information
        return {
            "question": request.question,
            "error": str(e)
        }
