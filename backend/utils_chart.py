from defog.llm.utils import chat_async
from utils_logging import LOGGER
import json

with open("./prompts/chart_edits/system.md", "r") as f:
    CHART_EDIT_SYSTEM_PROMPT = f.read()

with open("./prompts/chart_edits/user.md", "r") as f:
    CHART_EDIT_USER_PROMPT = f.read()

async def edit_chart(
    current_chart_state: dict,
    columns: list[str],
    user_request: str,
    model_name: str = "gpt-4o"
):
    """
    Edit a chart based on the current state and the columns available.
    """
    current_chart_state_str = json.dumps(current_chart_state, indent=4)
    columns_str = json.dumps(columns, indent=4)
    user_prompt = CHART_EDIT_USER_PROMPT.format(
        current_chart_state_str=current_chart_state_str,
        columns_str=columns_str,
        user_request=user_request,
    )
    response = await chat_async(
        model=model_name,
        messages = [
            {"role": "system", "content": CHART_EDIT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    LOGGER.info("Cost of generating chart edit: {:.2f} ¢".format(response.cost_in_cents))
    LOGGER.info("Time taken to generate chart edit: %s", response.time)

    response = response.content

    # parse the response
    if isinstance(response, str):
        if "```json" in response:
            response = response.split("```json")[1].strip()
            response = response.split("```")[0].strip()
        response_dict = json.loads(response)
    else:
        response_dict = response
    
    chart_state = response_dict.get("modified_chart_state") if "modified_chart_state" in response_dict else response_dict

    return chart_state