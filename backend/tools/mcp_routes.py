from auth_utils import validate_user_request
from fastapi import APIRouter, Depends
from request_models import AnswerQuestionFromDatabaseRequest
from utils_mcp import initialize_mcp_client
from utils_logging import LOGGER
import os
import json

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["MCP"],
)


@router.post("/answer_question_from_mcp")
async def answer_question_from_mcp_route(
    request: AnswerQuestionFromDatabaseRequest,
):
    """
    Route used for testing purposes.
    Generates an answer from a question using MCP servers listed in mcp_config.json
    """
    question = request.question
    model = request.model or "o3-mini"
    config_path = os.path.join(os.path.dirname(__file__), "mcp_config.json")

    # Initialize MCP client
    mcp_client = await initialize_mcp_client(config_path, model)
    if isinstance(mcp_client, dict) and "error" in mcp_client:
        # If there was an error initializing the client, return the error
        return mcp_client
    try:
        output = {"answer": "", "tool_outputs": []}
        output["answer"], output["tool_outputs"] = await mcp_client.mcp_chat(
            query=question
        )
        output["n_tool_calls"] = len(output["tool_outputs"])
    except Exception as e:
        error_msg = f"Failed to generate answer: {str(e)}"
        LOGGER.error(error_msg)
        return {"error": error_msg}
    finally:
        await mcp_client.cleanup()
    return output
