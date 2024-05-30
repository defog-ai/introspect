import datetime
import inspect
import json
import os
import trace
from uuid import uuid4
from colorama import Fore, Style
import traceback

import requests
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from agents.planner_executor.tool_helpers.rerun_step import rerun_step_and_dependents
from agents.planner_executor.tool_helpers.core_functions import analyse_data
from agents.planner_executor.tool_helpers.all_tools import tool_name_dict
import pandas as pd
from io import StringIO
from agents.main_agent import execute
from utils import get_clean_plan, get_db_type, log_msg

DEFOG_API_KEY = os.environ["DEFOG_API_KEY"]

from connection_manager import ConnectionManager
from db_utils import (
    add_to_recently_viewed_docs,
    add_tool,
    delete_tool,
    get_all_docs,
    get_analysis_versions,
    get_doc_data,
    get_report_data,
    get_tool_run,
    get_toolboxes,
    initialise_report,
    store_feedback,
    store_tool_run,
    toggle_disable_tool,
    update_doc_data,
    update_report_data,
    update_table_chart_data,
    get_table_data,
    get_all_analyses,
    update_tool_run_data,
    delete_doc,
    get_all_tools,
)

from utils import get_metadata

router = APIRouter()

manager = ConnectionManager()

import yaml

dfg_api_key = os.environ["DEFOG_API_KEY"]
llm_calls_url = os.environ["LLM_CALLS_URL"]
report_assets_dir = os.environ["REPORT_ASSETS_DIR"]


@router.post("/get_user_metadata")
async def get_user_metadata(request: Request):
    """
    Send the metadata, glossary, etc to the front end.
    """
    try:
        metadata_dets = await get_metadata()
        glossary = metadata_dets["glossary"]
        client_description = metadata_dets["client_description"]
        table_metadata_csv = metadata_dets["table_metadata_csv"]

        return {
            "success": True,
            "metadata": {
                "glossary": glossary,
                "client_description": client_description,
                "table_metadata_csv": table_metadata_csv,
            },
        }
    except Exception as e:
        print("Error getting metadata: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


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
                print("No document data provided.", data)
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
                print("Doc id is none ", data)
                continue

            col_name = "doc_blocks" if data.get("doc_blocks") else "doc_uint8"
            err = await update_doc_data(
                data.get("doc_id"),
                [col_name, "doc_title"],
                {col_name: data.get(col_name), "doc_title": data.get("doc_title")},
            )

            print(data.get("api_key"), data.get("username"), data.get("doc_id"))

            await manager.send_personal_message(data, websocket)
    except WebSocketDisconnect as e:
        # print("Disconnected. Error: ", e)
        # traceback.print_exc()
        manager.disconnect(websocket)
        await websocket.close()
    except Exception as e:
        # print("Disconnected. Error: ", e)
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
        username = data.get("username")
        api_key = DEFOG_API_KEY
        doc_id = data.get("doc_id")

        if username is None or type(username) != str:
            return {"success": False, "error_message": "Invalid username."}

        if doc_id is None or type(doc_id) != str:
            return {"success": False, "error_message": "Invalid document id."}

        await add_to_recently_viewed_docs(
            username=username,
            doc_id=doc_id,
            timestamp=str(datetime.datetime.now()),
        )

        return {"success": True}
    except Exception as e:
        print("Error getting analyses: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


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
    api_key = DEFOG_API_KEY
    doc_id = data.get("doc_id")
    username = data.get("username")
    col_name = data.get("col_name") or "doc_blocks"

    if api_key is None or type(api_key) != str:
        return {"success": False, "error_message": "Invalid api key."}

    if doc_id is None or type(doc_id) != str:
        return {"success": False, "error_message": "Invalid document id."}

    err, doc_data = await get_doc_data(doc_id, username, col_name)

    if err:
        return {"success": False, "error_message": err}

    return {"success": True, "doc_data": doc_data}


@router.post("/get_toolboxes")
async def get_toolboxes_endpoint(request: Request):
    """
    Get all toolboxes using the username.
    """
    try:
        data = await request.json()
        username = data.get("username")

        if username is None or type(username) != str:
            return {"success": False, "error_message": "Invalid username."}

        err, toolboxes = await get_toolboxes(username)
        if err:
            return {"success": False, "error_message": err}

        return {"success": True, "toolboxes": toolboxes}
    except Exception as e:
        print("Error getting analyses: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


@router.post("/get_docs")
async def get_docs(request: Request):
    """
    Get all documents of a user using the api key.
    """
    try:
        data = await request.json()
        username = data.get("username")

        if username is None or type(username) != str:
            return {"success": False, "error_message": "Invalid username."}

        err, own_docs, recently_viewed_docs = await get_all_docs(username)
        if err:
            return {"success": False, "error_message": err}

        return {
            "success": True,
            "docs": own_docs,
            "recently_viewed_docs": recently_viewed_docs,
        }
    except Exception as e:
        print("Error getting analyses: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


@router.post("/get_analyses")
async def get_analyses(request: Request):
    """
    Get all analysis of a user using the api key.
    """
    try:
        err, analyses = await get_all_analyses()
        if err:
            return {"success": False, "error_message": err}

        return {"success": True, "analyses": analyses}
    except Exception as e:
        print("Error getting analyses: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


@router.websocket("/table_chart")
async def update_table_chart(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "ping" in data:
                # don't do anything
                continue

            if data.get("table_id") is None:
                print("No table id ")
                continue

            if data.get("data") is None:
                print("No data given for table update")
                continue

            err, analysis, updated_data = await update_table_chart_data(
                data.get("table_id"), data.get("data")
            )

            if err is None:
                # run this table again
                print("Ran fine.")
                await manager.send_personal_message(
                    {"success": True, "run_again": True, "table_data": updated_data},
                    websocket,
                )
            elif err is not None:
                print("Error re running:", err)
                await manager.send_personal_message(
                    {"success": False, "run_again": True, "error_message": str(err)},
                    websocket,
                )

    except WebSocketDisconnect as e:
        # print("Disconnected. Error: ", e)
        # traceback.print_exc()
        manager.disconnect(websocket)
        await websocket.close()
    except Exception as e:
        # print("Disconnected. Error: ", e)
        traceback.print_exc()
        # other reasons for disconnect, like websocket being closed or a timeout
        manager.disconnect(websocket)
        await websocket.close()


@router.post("/get_table_chart")
async def get_table_chart(request: Request):
    """
    Get the table_chart using the id passed.
    """
    try:
        data = await request.json()
        table_id = data.get("table_id")

        if table_id is None or type(table_id) != str:
            return {"success": False, "error_message": "Invalid document id."}

        err, table_data = await get_table_data(table_id)

        if err:
            return {"success": False, "error_message": err}

        return {"success": True, "table_data": table_data}
    except Exception as e:
        print("Error getting analyses: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


@router.post("/get_tool_run")
async def get_tool_run_endpoint(request: Request):
    """
    Get the tool run using the id passed.
    """
    try:
        data = await request.json()
        tool_run_id = data.get("tool_run_id")
        print("getting tool run: ", tool_run_id)

        if tool_run_id is None or type(tool_run_id) != str:
            return {"success": False, "error_message": "Invalid tool run id."}

        err, tool_run = await get_tool_run(tool_run_id)

        if err:
            return {"success": False, "error_message": err}

        return {"success": True, "tool_run_data": tool_run}
    except Exception as e:
        print("Error getting analyses: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": "Unable to parse your request."}


@router.websocket("/edit_tool_run")
async def edit_tool_run(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if "ping" in data:
                # don't do anything
                continue

            if data.get("tool_run_id") is None:
                print("No tool run id ")
                continue

            if data.get("analysis_id") is None:
                print("No analysis id ")
                continue

            update_res = await update_tool_run_data(
                data.get("analysis_id"),
                data.get("tool_run_id"),
                data.get("update_prop"),
                data.get("new_val"),
            )
            if not update_res["success"]:
                print(
                    f"{Fore.RED} {Style.Bright} Error updating tool run: {update_res['error_message']}{Style.RESET_ALL}"
                )

    except WebSocketDisconnect as e:
        # print("Disconnected. Error: ", e)
        # traceback.print_exc()
        manager.disconnect(websocket)
        await websocket.close()
    except Exception as e:
        # print("Disconnected. Error: ", e)
        traceback.print_exc()
        # other reasons for disconnect, like websocket being closed or a timeout
        manager.disconnect(websocket)
        await websocket.close()


@router.websocket("/step_rerun")
async def rerun_step(websocket: WebSocket):
    """
    Re run a step (and associated steps) in the analysis.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "ping" in data:
                # don't do anything
                continue

            tool_run_id = data.get("tool_run_id")
            analysis_id = data.get("analysis_id")

            if tool_run_id is None or type(tool_run_id) != str:
                return {"success": False, "error_message": "Invalid tool run id."}

            if analysis_id is None or type(analysis_id) != str:
                return {"success": False, "error_message": "Invalid analysis id."}

            # get steps from db
            err, analysis_data = get_report_data(analysis_id)
            if err:
                return {
                    "success": False,
                    "error_message": err,
                    "tool_run_id": tool_run_id,
                    "analysis_id": analysis_id,
                }

            metadata_dets = await get_metadata()
            glossary = metadata_dets["glossary"]
            client_description = metadata_dets["client_description"]
            table_metadata_csv = metadata_dets["table_metadata_csv"]

            global_dict = {
                "user_question": analysis_data["user_question"],
                "table_metadata_csv": table_metadata_csv,
                "client_description": client_description,
                "glossary": glossary,
                "llm_calls_url": llm_calls_url,
                "report_assets_dir": report_assets_dir,
            }

            if err:
                return {
                    "success": False,
                    "error_message": err,
                    "tool_run_id": tool_run_id,
                    "analysis_id": analysis_id,
                }

            steps = analysis_data["gen_steps"]
            if steps["success"]:
                steps = steps["steps"]
            else:
                return {
                    "success": False,
                    "error_message": steps["error_message"],
                    "tool_run_id": tool_run_id,
                    "analysis_id": analysis_id,
                }

            print([s["inputs"] for s in steps])
            async for err, reran_id, new_data in rerun_step_and_dependents(
                analysis_id, tool_run_id, steps, global_dict=global_dict
            ):
                if new_data and type(new_data) == dict:
                    if reran_id:
                        print("Reran step: ", reran_id)
                        await manager.send_personal_message(
                            {
                                "success": True,
                                "tool_run_id": reran_id,
                                "analysis_id": analysis_id,
                                "tool_run_data": new_data,
                            },
                            websocket,
                        )
                    elif new_data.get("pre_tool_run_message"):
                        print(
                            f"Starting rerunning of step: {new_data.get('pre_tool_run_message')} with websocket: {websocket} in application_state: {websocket.application_state} and client_state: {websocket.client_state}"
                        )
                        await manager.send_personal_message(
                            {
                                "pre_tool_run_message": new_data.get(
                                    "pre_tool_run_message"
                                ),
                                "analysis_id": analysis_id,
                            },
                            websocket,
                        )
                else:
                    print("Error: ", err)
                    await manager.send_personal_message(
                        {
                            "success": False,
                            "error_message": err,
                            "tool_run_id": reran_id,
                            "analysis_id": analysis_id,
                        },
                        websocket,
                    )

    except WebSocketDisconnect as e:
        print("Disconnected. Error: ", e)
        # traceback.print_exc()
        manager.disconnect(websocket)
        await websocket.close()
    except Exception as e:
        # print("Disconnected. Error: ", e)
        traceback.print_exc()
        # other reasons for disconnect, like websocket being closed or a timeout
        manager.disconnect(websocket)
        await websocket.close()


# setup an analyse_data websocket endpoint
@router.websocket("/analyse_data")
async def analyse_data_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "ping" in data:
                # don't do anything
                continue
            if data.get("question") is None:
                await manager.send_personal_message(
                    {"success": False, "error_message": "No question"}, websocket
                )
                continue

            if data.get("data") is None:
                await manager.send_personal_message(
                    {"success": False, "error_message": "No data"}, websocket
                )
                continue

            # read data from the csv
            df = pd.read_csv(StringIO(data.get("data")))
            image_path = data.get("image")

            async for chunk in analyse_data(
                data.get("question"), df, image_path=image_path
            ):
                await manager.send_personal_message(chunk, websocket)

    except WebSocketDisconnect as e:
        # print("Disconnected. Error: ", e)
        # traceback.print_exc()
        manager.disconnect(websocket)
        await websocket.close()
    except Exception as e:
        # print("Disconnected. Error: ", e)
        traceback.print_exc()
        await manager.send_personal_message(
            {"success": False, "error_message": str(e)[:300]}, websocket
        )
        # other reasons for disconnect, like websocket being closed or a timeout
        manager.disconnect(websocket)
        await websocket.close()


@router.post("/create_new_step")
async def create_new_step(request: Request):
    """
    This is called when a user adds a step on the front end.
    This will receive a tool name, and tool inputs.
    This will create a new step in the analysis.
    No tool run will occur. Though a tool run id will be created for this step in case rerun is called in the future.
    """
    try:
        data = await request.json()
        # check if this has analysis_id, tool_name and parent_step, and inputs
        analysis_id = data.get("analysis_id")
        tool_name = data.get("tool_name")
        parent_step = data.get("parent_step")
        inputs = data.get("inputs")
        outputs_storage_keys = data.get("outputs_storage_keys")

        if analysis_id is None or type(analysis_id) != str:
            return {"success": False, "error_message": "Invalid analysis id."}

        if (
            tool_name is None
            or type(tool_name) != str
            or tool_name not in tool_name_dict
        ):
            return {"success": False, "error_message": "Invalid tool name."}

        if parent_step is None or type(parent_step) != dict:
            return {"success": False, "error_message": "Invalid parent step."}

        if inputs is None or type(inputs) != dict:
            return {"success": False, "error_message": "Invalid inputs."}

        if outputs_storage_keys is None or type(outputs_storage_keys) != list:
            return {"success": False, "error_message": "Invalid outputs provided."}

        if len(outputs_storage_keys) == 0:
            return {"success": False, "error_message": "Please type in output names."}

        # if any of the outputs are empty or aren't strings
        if any([not o or type(o) != str for o in outputs_storage_keys]):
            return {
                "success": False,
                "error_message": "Outputs provided are either blank or incorrect.",
            }

        # try to get this analysis' data
        err, analysis_data = get_report_data(analysis_id)
        if err:
            return {"success": False, "error_message": err}

        # get the steps
        steps = analysis_data.get("gen_steps")
        if steps and steps["success"]:
            steps = steps["steps"]
        else:
            return {
                "success": False,
                "error_message": (
                    steps.get("error_message")
                    if steps is not None
                    else "No steps found for analysis"
                ),
            }

        err, tools = get_all_tools()
        if err:
            return {"success": False, "error_message": err}

        tool = tools[tool_name]

        new_tool_run_id = str(uuid4())

        # a new empty step
        new_step = {
            "tool_name": tool_name,
            "model_generated_inputs": inputs,
            "inputs": inputs,
            "input_metadata": tool["input_metadata"],
            "tool_run_id": new_tool_run_id,
            "outputs_storage_keys": outputs_storage_keys,
        }

        # add a step with the given inputs and tool_name
        steps.append(new_step)

        # store a empty tool run
        store_result = await store_tool_run(
            analysis_id,
            new_step,
            {
                "success": True,
                "code_str": tool["code"],
            },
            skip_step_update=True,
        )

        if not store_result["success"]:
            return store_result

        # update report data
        update_err = await update_report_data(analysis_id, "gen_steps", [new_step])

        if update_err:
            return {"success": False, "error_message": update_err}

        return {
            "success": True,
            "new_step": new_step,
            "tool_run_id": new_tool_run_id,
        }

    except Exception as e:
        print("Error creating new step: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}
    return


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
        print("Error deleting doc: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


# download csv using tool_run_id and output_storage_key
@router.post("/download_csv")
async def download_csv(request: Request):
    """
    Download a csv using the tool run id and output storage key.
    """
    try:
        data = await request.json()
        tool_run_id = data.get("tool_run_id")
        output_storage_key = data.get("output_storage_key")
        analysis_id = data.get("analysis_id")

        if tool_run_id is None or type(tool_run_id) != str:
            return {"success": False, "error_message": "Invalid tool run id."}

        if output_storage_key is None or type(output_storage_key) != str:
            return {"success": False, "error_message": "Invalid output storage key."}

        if analysis_id is None or type(analysis_id) != str:
            return {"success": False, "error_message": "Invalid analysis id."}

        # first try to find this file in the file system
        f_name = tool_run_id + "_output-" + output_storage_key + ".feather"
        f_path = os.path.join(report_assets_dir, "datasets", f_name)

        if not os.path.isfile(f_path):
            log_msg(
                f"Input {output_storage_key} not found in the file system. Rerunning step: {tool_run_id}"
            )
            # re run this step
            # get steps from db
            err, analysis_data = get_report_data(analysis_id)
            if err:
                return {"success": False, "error_message": err}

            metadata_dets = await get_metadata()
            glossary = metadata_dets["glossary"]
            client_description = metadata_dets["client_description"]
            table_metadata_csv = metadata_dets["table_metadata_csv"]

            global_dict = {
                "user_question": analysis_data["user_question"],
                "table_metadata_csv": table_metadata_csv,
                "client_description": client_description,
                "glossary": glossary,
                "llm_calls_url": llm_calls_url,
                "report_assets_dir": report_assets_dir,
            }

            if err:
                return {"success": False, "error_message": err}

            steps = analysis_data.get("gen_steps")
            if steps and steps.get("success") and steps.get("steps"):
                steps = steps["steps"]
            else:
                return {"success": False, "error_message": steps["error_message"]}

            async for err, reran_id, new_data in rerun_step_and_dependents(
                analysis_id, tool_run_id, steps, global_dict=global_dict
            ):
                # don't need to yield unless there's an error
                # if error, then bail
                if err:
                    return {"success": False, "error_message": err}
        else:
            log_msg(
                f"Input {output_storage_key} found in the file system. No need to rerun step."
            )

        # now the file *should* be available
        df = pd.read_feather(f_path)

        return {
            "success": True,
            "tool_run_id": tool_run_id,
            "output_storage_key": output_storage_key,
            # get it as a csv string
            "csv": df.to_csv(index=False),
        }

    except Exception as e:
        print("Error downloading csv: ", e)
        traceback.print_exc()
        return {"success": False, "error_message": str(e)[:300]}


# an endpoint to delete steps.
# we will get a list of tool run ids
# we will remove these from the analysis


@router.post("/delete_steps")
async def delete_steps(request: Request):
    """
    Delete steps using the tool run ids passed.
    """
    try:
        data = await request.json()
        tool_run_ids = data.get("tool_run_ids")
        analysis_id = data.get("analysis_id")

        if tool_run_ids is None or type(tool_run_ids) != list:
            return {"success": False, "error_message": "Invalid tool run ids."}

        if analysis_id is None or type(analysis_id) != str:
            return {"success": False, "error_message": "Invalid analysis id."}

        # try to get this analysis' data
        err, analysis_data = get_report_data(analysis_id)
        if err:
            return {"success": False, "error_message": err}

        # get the steps
        steps = analysis_data.get("gen_steps")
        if steps and steps["success"]:
            steps = steps["steps"]
        else:
            return {
                "success": False,
                "error_message": (
                    steps.get("error_message")
                    if steps is not None
                    else "No steps found for analysis"
                ),
            }

        # remove the steps with these tool run ids
        new_steps = [s for s in steps if s["tool_run_id"] not in tool_run_ids]

        # # # update report data
        update_err = await update_report_data(
            analysis_id, "gen_steps", new_steps, replace=True
        )

        if update_err:
            return {"success": False, "error_message": update_err}

        return {"success": True, "new_steps": new_steps}

    except Exception as e:
        print("Error deleting steps: ", e)
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
        
        print("Deleted tool: ", function_name)

        return {"success": True}
    except Exception as e:
        print("Error disabling tool: ", e)
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

        print("Toggled tool: ", function_name)

        return {"success": True}
    except Exception as e:
        print("Error disabling tool: ", e)
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
        toolbox = data.get("toolbox")
        no_code = data.get("no_code", False)

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

        if toolbox is None or type(toolbox) != str or len(toolbox) == 0:
            return {"success": False, "error_message": "Invalid toolbox."}

        if no_code is None or type(no_code) != bool:
            return {"success": False, "error_message": "Invalid no code."}

        err = await add_tool(
            tool_name,
            function_name,
            description,
            code,
            input_metadata,
            output_metadata,
            toolbox,
            no_code,
        )

        if err:
            raise Exception(err)

        print("Added tool: ", function_name)

        return {"success": True}
    except Exception as e:
        print("Error adding tool: ", e)
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
        username = data.get("username")
        api_key = DEFOG_API_KEY

        # get metadata
        m = await get_metadata()
        metadata = m["table_metadata_csv"]
        client_description = m["client_description"]
        glossary = m["glossary"]

        db_type = get_db_type()

        if analysis_id is None or type(analysis_id) != str:
            raise Exception("Invalid analysis id.")

        if api_key is None or type(api_key) != str:
            raise Exception("Invalid api key.")

        if user_question is None or type(user_question) != str:
            raise Exception("Invalid user question.")

        err, analysis_data = get_report_data(analysis_id)
        if err:
            raise Exception(err)

        cleaned_plan = get_clean_plan(analysis_data)

        generated_plan_yaml = yaml.dump(cleaned_plan)

        # store in the defog_plans_feedback table
        err, did_overwrite = await store_feedback(
            username,
            user_question,
            analysis_id,
            is_correct,
            comments,
            metadata,
            client_description,
            glossary,
            db_type,
        )

        # send the following to the defog server, and get feedback on how to improve it
        # - user_question
        # - comments
        # - metadata
        # - glossary
        # - plan generated
        if not is_correct:
            err, tools = get_all_tools()
            tools = [
                {
                    "function_name": tools[tool]["function_name"],
                    "description": tools[tool]["description"],
                    "input_metadata": tools[tool]["input_metadata"],
                    "output_metadata": tools[tool]["output_metadata"],
                }
                for tool in tools
            ]

            tool_description_yaml = yaml.dump(tools)

            # TODO: implement this on the defog server
            r = requests.post(
                "https://api.defog.ai/reflect_on_agent_feedback",
                json={
                    "question": user_question,
                    "comments": comments,
                    "plan_generated": generated_plan_yaml,
                    "api_key": DEFOG_API_KEY,
                    "tool_description": tool_description_yaml,
                },
            )

            # we will get back:
            # - updated metadata
            # - updated glossary
            # - updated golden plan
            raw_response = r.json()["diagnosis"]

            # extract yaml from metadata
            initial_recommended_plan = (
                raw_response.split("```yaml")[-1].split("```")[0].strip()
            )
            print(initial_recommended_plan, flush=True)
            new_analysis_id = str(uuid4())
            new_analysis_data = None
            try:
                initial_recommended_plan = yaml.safe_load(initial_recommended_plan)
                # give each tool a tool_run_id
                # duplicate model_generated_inputs to inputs
                for i, item in enumerate(initial_recommended_plan):
                    item["tool_run_id"] = str(uuid4())
                    item["inputs"] = item["model_generated_inputs"].copy()

                # create a new analysis with these as steps
                err, new_analysis_data = await initialise_report(
                    user_question,
                    username,
                    new_analysis_id,
                    {"gen_steps": [], "clarify": []},
                )
                if err:
                    raise Exception(err)

                # run the steps
                metadata_dets = await get_metadata()
                glossary = metadata_dets["glossary"]
                client_description = metadata_dets["client_description"]
                table_metadata_csv = metadata_dets["table_metadata_csv"]

                setup, post_process = await execute(
                    report_id=new_analysis_id,
                    user_question=user_question,
                    client_description=client_description,
                    table_metadata_csv=table_metadata_csv,
                    assignment_understanding="",
                    glossary=glossary,
                    toolboxes=[],
                    parent_analyses=[],
                    similar_plans=[],
                    predefined_steps=initial_recommended_plan,
                )

                if not setup.get("success"):
                    raise Exception(setup.get("error_message", ""))

                final_executed_plan = []
                # run the generator
                if "generator" in setup:
                    g = setup["generator"]
                    async for step in g():
                        # step comes in as a list of 1 step
                        final_executed_plan += step
                        err = await update_report_data(
                            new_analysis_id, "gen_steps", step
                        )
                        if err:
                            raise Exception(err)

                recommended_plan = final_executed_plan
            except Exception as e:
                print(e)
                traceback.print_exc()
                recommended_plan = None
                new_analysis_data = None

            if err is not None:
                raise Exception(err)

            return {
                "success": True,
                "did_overwrite": did_overwrite,
                "suggested_improvements": raw_response,
                "recommended_plan": recommended_plan,
                "new_analysis_id": new_analysis_id,
                "new_analysis_data": new_analysis_data,
            }
        else:
            return {"success": True, "did_overwrite": did_overwrite}

    except Exception as e:
        print(str(e))
        error = str(e)[:300]
        print(error)
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
        print("Error getting analysis versions: ", e)
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
        print("Error adding analysis to dashboard: ", e)
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Unable to add analysis to dashboard: " + str(e)[:300],
        }
