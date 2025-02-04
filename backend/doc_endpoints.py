import os
import traceback

from fastapi import APIRouter, Request
from agents.planner_executor.planner_executor_agent import rerun_step
import logging
from generic_utils import get_api_key_from_key_name

logging.basicConfig(level=logging.INFO)

from connection_manager import ConnectionManager
from db_utils import (
    get_analysis_data,
    get_all_tools,
)

router = APIRouter()

manager = ConnectionManager()

llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")


# download csv using step_id and output_storage_key
@router.post("/download_csv")
async def download_csv(request: Request):
    """
    Download a csv using the step id and output storage key.
    """
    try:
        data = await request.json()
        step_id = data.get("step_id")
        output_storage_key = data.get("output_storage_key")
        analysis_id = data.get("analysis_id")
        key_name = data.get("key_name")
        api_key = get_api_key_from_key_name(key_name)

        if step_id is None or type(step_id) != str:
            return {"success": False, "error_message": "Invalid tool run id."}

        if output_storage_key is None or type(output_storage_key) != str:
            return {"success": False, "error_message": "Invalid output storage key."}

        if analysis_id is None or type(analysis_id) != str:
            return {"success": False, "error_message": "Invalid analysis id."}

        # re run this step
        # get steps from db
        err, analysis_data = await get_analysis_data(analysis_id)
        if err:
            raise Exception(err)

        # get the steps
        all_steps = analysis_data.get("gen_steps")
        if all_steps and all_steps["success"]:
            all_steps = all_steps["steps"]
        else:
            raise Exception("No steps found in analysis data")

        # get the target step
        target_step = None
        for step in all_steps:
            if step["id"] == step_id:
                target_step = step
                break

        if target_step is None:
            raise Exception("Request step not found in analysis data")

        analysis_data = await rerun_step(
            step=target_step,
            all_steps=all_steps,
            dfg_api_key=api_key,
            analysis_id=analysis_id,
            user_question=None,
            dev=False,
            temp=False,
        )

        csv = analysis_data[0]['outputs']['answer']['data']

        return {
            "success": True,
            "step_id": step_id,
            "output_storage_key": output_storage_key,
            # get it as a csv string
            "csv": csv,
        }

    except Exception as e:
        logging.info("Error downloading csv: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


@router.post("/get_user_tools")
async def get_user_tools(request: Request):
    """
    Get all tools available to the user.
    """
    err, tools = await get_all_tools()
    if err:
        return {"success": False, "error_message": err}
    return {"success": True, "tools": tools}


