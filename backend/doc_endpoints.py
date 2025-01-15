import datetime
import os
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from agents.planner_executor.tool_helpers.core_functions import analyse_data
import pandas as pd
from agents.planner_executor.planner_executor_agent import rerun_step
import logging
from generic_utils import get_api_key_from_key_name
from db_utils import get_db_type_creds

logging.basicConfig(level=logging.INFO)

from connection_manager import ConnectionManager
from db_utils import (
    add_tool,
    delete_tool,
    get_analysis_data,
    store_feedback,
    toggle_disable_tool,
    get_all_tools,
)

router = APIRouter()

manager = ConnectionManager()

llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")
analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)


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

        # first try to find this file in the file system
        f_name = step_id + "_output-" + output_storage_key + ".feather"
        f_path = os.path.join(analysis_assets_dir, "datasets", f_name)

        logging.info("lansdfgljansdl")

        if not os.path.isfile(f_path):
            logging.info(
                f"Input {output_storage_key} not found in the file system. Rerunning step: {step_id}"
            )
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

            _ = await rerun_step(
                step=target_step,
                all_steps=all_steps,
                dfg_api_key=api_key,
                analysis_id=analysis_id,
                user_question=None,
                dev=False,
                temp=False,
            )
        else:
            logging.info(
                f"Input {output_storage_key} found in the file system. No need to rerun step."
            )

        # now the file *should* be available
        df = pd.read_feather(f_path)

        return {
            "success": True,
            "step_id": step_id,
            "output_storage_key": output_storage_key,
            # get it as a csv string
            "csv": df.to_csv(index=False),
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
    err, tools = get_all_tools()
    if err:
        return {"success": False, "error_message": err}
    return {"success": True, "tools": tools}


@router.post("/delete_tool")
async def delete_tool_endpoint(request: Request):
    """
    Delete a tool using the tool name.
    """
    try:
        data = await request.json()
        function_name = data.get("function_name")

        if function_name is None or type(function_name) != str:
            return {"success": False, "error_message": "Invalid tool name."}

        err = await delete_tool(function_name)

        if err:
            return {"success": False, "error_message": err}

        logging.info("Deleted tool: " + function_name)

        return {"success": True}
    except Exception as e:
        logging.info("Error disabling tool: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


@router.post("/toggle_disable_tool")
async def toggle_disable_tool_endpoint(request: Request):
    """
    Toggle the disabled property of a tool using the tool name.
    """
    try:
        data = await request.json()
        function_name = data.get("function_name")

        if function_name is None or type(function_name) != str:
            return {"success": False, "error_message": "Invalid tool name."}

        err = await toggle_disable_tool(function_name)

        if err:
            raise Exception(err)

        return {"success": True}
    except Exception as e:
        logging.info("Error disabling tool: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


@router.post("/add_tool")
async def add_tool_endpoint(request: Request):
    """
    Add a tool to the defog_tools table.
    """
    try:
        data = await request.json()
        tool_name = data.get("tool_name")
        function_name = data.get("function_name")
        description = data.get("description")
        code = data.get("code")
        input_metadata = data.get("input_metadata")
        output_metadata = data.get("output_metadata")
        no_code = data.get("no_code", False)
        key_name = data.get("key_name")
        api_key = get_api_key_from_key_name(key_name)

        if (
            function_name is None
            or type(function_name) != str
            or len(function_name) == 0
        ):
            return {"success": False, "error_message": "Invalid tool name."}

        if description is None or type(description) != str or len(description) == 0:
            return {"success": False, "error_message": "Invalid description."}

        if code is None or type(code) != str or len(code) == 0:
            return {"success": False, "error_message": "Invalid code."}

        if input_metadata is None or type(input_metadata) != dict:
            return {"success": False, "error_message": "Invalid input_metadata."}

        if (
            output_metadata is None
            or type(output_metadata) != list
            or len(output_metadata) == 0
        ):
            return {
                "success": False,
                "error_message": "Invalid or empty output_metadata.",
            }

        if tool_name is None or type(tool_name) != str or len(tool_name) == 0:
            return {"success": False, "error_message": "Invalid display name."}

        if no_code is None or type(no_code) != bool:
            return {"success": False, "error_message": "Invalid no code."}

        err = await add_tool(
            api_key=api_key,
            tool_name=tool_name,
            function_name=function_name,
            description=description,
            code=code,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
        )

        if err:
            raise Exception(err)

        logging.info("Added tool: " + function_name)

        return {"success": True}
    except Exception as e:
        logging.info("Error adding tool: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


@router.post("/submit_feedback")
async def submit_feedback(request: Request):
    """
    Submit feedback to the backend.
    """
    error = None
    try:
        data = await request.json()
        analysis_id = data.get("analysis_id")
        comments = data.get("comments", {})
        is_correct = data.get("is_correct", False)
        user_question = data.get("user_question")
        analysis_id = data.get("analysis_id")
        token = data.get("token")
        key_name = data.get("key_name")
        api_key = get_api_key_from_key_name(key_name)
        res = await get_db_type_creds(api_key)
        db_type = res[0]

        if analysis_id is None or type(analysis_id) != str:
            raise Exception("Invalid analysis id.")

        if api_key is None or type(api_key) != str:
            raise Exception("Invalid api key.")

        if user_question is None or type(user_question) != str:
            raise Exception("Invalid user question.")

        err, analysis_data = await get_analysis_data(analysis_id)

        # store in the defog_plans_feedback table
        err, did_overwrite = await store_feedback(
            api_key=api_key,
            user_question=user_question,
            analysis_id=analysis_id,
            is_correct=is_correct,
            comments=comments,
            db_type=db_type,
        )

        if err:
            raise Exception(err)

        return {"success": True, "did_overwrite": did_overwrite}
    except Exception as e:
        logging.info(str(e))
        error = str(e)[:300]
        logging.info(error)
        traceback.print_exc()
        return {"success": False, "error_message": error}
