import datetime
from colorama import Fore, Style
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from agents.planner_executor.tool_helpers.rerun_step import rerun_step_and_dependents

DEFOG_API_KEY = "genmab-survival-test"

from connection_manager import ConnectionManager
from db_utils import (
    add_to_recently_viewed_docs,
    get_all_docs,
    get_doc_data,
    get_report_data,
    get_tool_run,
    get_toolboxes,
    update_doc_data,
    update_table_chart_data,
    get_table_data,
    get_all_analyses,
    update_tool_run_data,
)

from utils import table_metadata_csv, client_description, glossary

router = APIRouter()

manager = ConnectionManager()

import yaml

with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

dfg_api_key = env["api_key"]


@router.websocket("/docs")
async def doc_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
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

            if (
                data.get("api_key") is not None
                and data.get("username") is not None
                and err is None
            ):
                await add_to_recently_viewed_docs(
                    username=data.get("username"),
                    api_key=data.get("api_key"),
                    doc_id=data.get("doc_id"),
                    timestamp=str(datetime.datetime.now()),
                )

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


@router.post("/get_doc")
async def get_document(request: Request):
    """
    Get the document using the id passed.
    If it doesn't exist, create one and return empty data.
    This should be safe because we're validating the api key on the front end.
    But validate it here again jic.
    """
    data = await request.json()
    api_key = data.get("api_key")
    doc_id = data.get("doc_id")
    username = data.get("username")
    col_name = data.get("col_name") or "doc_blocks"

    if api_key is None or type(api_key) != str:
        return {"success": False, "error_message": "Invalid api key."}

    if doc_id is None or type(doc_id) != str:
        return {"success": False, "error_message": "Invalid document id."}

    err, doc_data = await get_doc_data(doc_id, api_key, username, col_name)

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
        # api_key = data.get("api_key")
        api_key = DEFOG_API_KEY

        if api_key is None or type(api_key) != str:
            return {"success": False, "error_message": "Invalid api key."}

        err, own_docs, recently_viewed_docs = await get_all_docs(api_key)
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
        data = await request.json()
        api_key = data.get("api_key")

        if api_key is None or type(api_key) != str:
            return {"success": False, "error_message": "Invalid api key."}

        err, analyses = await get_all_analyses(api_key)
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
            run_again = data.get("run_again")
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
            print(data)
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
            print(data)
            tool_run_id = data.get("tool_run_id")
            analysis_id = data.get("analysis_id")

            if tool_run_id is None or type(tool_run_id) != str:
                return {"success": False, "error_message": "Invalid tool run id."}

            if analysis_id is None or type(analysis_id) != str:
                return {"success": False, "error_message": "Invalid analysis id."}

            # get steps from db
            err, analysis_data = get_report_data(analysis_id)

            global_dict = {
                "user_question": analysis_data["user_question"],
                "table_metadata_csv": table_metadata_csv,
                "client_description": client_description,
                "glossary": glossary,
            }

            if err:
                return {"success": False, "error_message": err}

            steps = analysis_data["gen_steps"]
            if steps["success"]:
                steps = steps["steps"]
            else:
                return {"success": False, "error_message": steps["error_message"]}

            print([s["inputs"] for s in steps])
            async for err, reran_id, new_data in rerun_step_and_dependents(
                analysis_id, tool_run_id, steps, global_dict=global_dict
            ):
                print("Error: ", err)
                print("Reran step: ", reran_id)
                # print("New data: ", new_data)
                if new_data:
                    await manager.send_personal_message(
                        {
                            "success": True,
                            "tool_run_id": reran_id,
                            "tool_run_data": new_data,
                        },
                        websocket,
                    )
                else:
                    await manager.send_personal_message(
                        {
                            "success": False,
                            "error_message": err,
                            "tool_run_id": reran_id,
                        },
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
