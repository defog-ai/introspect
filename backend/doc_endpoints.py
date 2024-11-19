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
    add_to_recently_viewed_docs,
    add_tool,
    delete_tool,
    get_all_docs,
    get_analysis_versions,
    get_doc_data,
    get_analysis_data,
    store_feedback,
    toggle_disable_tool,
    update_doc_data,
    get_all_analyses,
    delete_doc,
    get_all_tools,
)

router = APIRouter()

manager = ConnectionManager()

llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")
analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)


@router.websocket("/docs")
async def doc_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "ping" in data:
                # don't do anything
                continue
            if data.get("doc_uint8") is None:
                logging.info("No document data provided.")
                logging.info(data)
                # send error back
                await manager.send_personal_message(
                    {"success": False, "error_message": "No document data provided."},
                    websocket,
                )
                continue

            if data.get("doc_id") is None:
                await manager.send_personal_message(
                    {"success": False, "error_message": "No document id provided."},
                    websocket,
                )
                logging.info("Doc id is none ")
                logging.info(data)

                continue

            col_name = "doc_blocks" if data.get("doc_blocks") else "doc_uint8"
            err = await update_doc_data(
                data.get("doc_id"),
                [col_name, "doc_title"],
                {col_name: data.get(col_name), "doc_title": data.get("doc_title")},
            )

            logging.info(data.get("api_key"))
            logging.info(data.get("token"))
            logging.info(data.get("doc_id"))

            await manager.send_personal_message(data, websocket)
    except WebSocketDisconnect as e:
        # logging.info("Disconnected. Error: " +  str(e))
        # traceback.print_exc()
        manager.disconnect(websocket)
        await websocket.close()
    except Exception as e:
        # logging.info("Disconnected. Error: " +  str(e))
        # traceback.print_exc()
        # other reasons for disconnect, like websocket being closed or a timeout
        manager.disconnect(websocket)
        await websocket.close()


@router.post("/add_to_recently_viewed_docs")
async def add_to_recently_viewed_docs_endpoint(request: Request):
    """
    Add a document to the recently viewed docs of a user.
    """
    try:
        data = await request.json()
        token = data.get("token")
        key_name = data.get("key_name")
        api_key = get_api_key_from_key_name(key_name)

        doc_id = data.get("doc_id")

        if token is None or type(token) != str:
            return {"success": False, "error_message": "Invalid token."}

        if doc_id is None or type(doc_id) != str:
            return {"success": False, "error_message": "Invalid document id."}

        err = await add_to_recently_viewed_docs(
            token=token,
            doc_id=doc_id,
            api_key=api_key,
            timestamp=str(datetime.datetime.now()),
        )

        if err:
            raise Exception(err)

        return {"success": True}
    except Exception as e:
        logging.info("Error getting analyses: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": e}


@router.post("/toggle_archive_status")
async def toggle_archive_status(request: Request):
    """
    Toggle the archive status of a document.
    """
    data = await request.json()
    doc_id = data.get("doc_id")
    archive_status = data.get("archive_status")

    err = await update_doc_data(doc_id, ["archived"], {"archived": archive_status})

    if err:
        return {"success": False, "error_message": err}

    return {"success": True}


@router.post("/get_doc")
async def get_document(request: Request):
    """
    Get the document using the id passed.
    If it doesn't exist, create one and return empty data.
    """
    data = await request.json()
    key_name = data.get("key_name")
    doc_id = data.get("doc_id")
    token = data.get("token")
    col_name = data.get("col_name") or "doc_blocks"
    api_key = get_api_key_from_key_name(key_name)

    if api_key is None or type(api_key) != str:
        return {"success": False, "error_message": "Invalid api key."}

    if doc_id is None or type(doc_id) != str:
        return {"success": False, "error_message": "Invalid document id."}

    err, doc_data = await get_doc_data(
        api_key=api_key, doc_id=doc_id, token=token, col_name=col_name
    )

    if err:
        return {"success": False, "error_message": err}

    return {"success": True, "doc_data": doc_data}


@router.post("/get_docs")
async def get_docs(request: Request):
    """
    Get all documents of a user using the api key.
    """
    try:
        data = await request.json()
        token = data.get("token")

        if token is None or type(token) != str:
            return {"success": False, "error_message": "Invalid token."}

        err, own_docs, recently_viewed_docs = await get_all_docs(token)
        if err:
            return {"success": False, "error_message": err}

        return {
            "success": True,
            "docs": own_docs,
            "recently_viewed_docs": recently_viewed_docs,
        }
    except Exception as e:
        logging.info("Error getting analyses: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


@router.post("/get_analyses")
async def get_analyses(request: Request):
    """
    Get all analysis of a user using the api key.
    """
    params = await request.json()
    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    print(api_key, flush=True)
    try:
        err, analyses = await get_all_analyses(api_key=api_key)
        if err:
            return {"success": False, "error_message": err}

        return {"success": True, "analyses": analyses}
    except Exception as e:
        logging.info("Error getting analyses: " + str(e))
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


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
            err, analysis_data = get_analysis_data(analysis_id)
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


@router.post("/delete_doc")
async def delete_doc_endpoint(request: Request):
    """
    Delete a document using the id passed.
    """
    try:
        data = await request.json()
        doc_id = data.get("doc_id")

        if doc_id is None or type(doc_id) != str:
            return {"success": False, "error_message": "Invalid document id."}

        err = await delete_doc(doc_id)

        if err:
            return {"success": False, "error_message": err}

        return {"success": True}
    except Exception as e:
        logging.info("Error deleting doc: " + str(e))
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
        res = get_db_type_creds(api_key)
        db_type = res[0]

        if analysis_id is None or type(analysis_id) != str:
            raise Exception("Invalid analysis id.")

        if api_key is None or type(api_key) != str:
            raise Exception("Invalid api key.")

        if user_question is None or type(user_question) != str:
            raise Exception("Invalid user question.")

        err, analysis_data = get_analysis_data(analysis_id)

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


@router.post("/get_analysis_versions")
async def get_analysis_versions_endpoint(request: Request):
    # get all analysis ids that have teh suffix -v1, -v2, -v3 etc
    try:
        params = await request.json()
        root_analysis_id = params.get("root_analysis_id", None)

        if not root_analysis_id:
            raise Exception("No root analysis provided.")

        await get_analysis_versions(root_analysis_id)
        pass
    except Exception as e:
        logging.info("Error getting analysis versions: " + str(e))
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Unable to get versions: " + str(e[:300]),
        }


@router.post("/update_dashboard_data")
async def update_dashboard_data_endpoint(request: Request):
    try:
        data = await request.json()
        if data.get("doc_uint8") is None:
            return {"success": False, "error_message": "No document data provided."}

        if data.get("doc_id") is None:
            return {"success": False, "error_message": "No document id provided."}

        col_name = "doc_blocks" if data.get("doc_blocks") else "doc_uint8"
        err = await update_doc_data(
            data.get("doc_id"),
            [col_name, "doc_title"],
            {col_name: data.get(col_name), "doc_title": data.get("doc_title")},
        )
        if err:
            return {"success": False, "error_message": err}

        return {"success": True}
    except Exception as e:
        logging.info("Error adding analysis to dashboard: " + str(e))
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Unable to add analysis to dashboard: " + str(e)[:300],
        }
