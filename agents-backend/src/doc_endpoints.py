import datetime
import inspect
import os
from uuid import uuid4
from colorama import Fore, Style
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from agents.planner_executor.tool_helpers.rerun_step import rerun_step_and_dependents
from agents.planner_executor.tool_helpers.core_functions import analyse_data
from agents.planner_executor.tool_helpers.all_tools import tool_name_dict
from agents.planner_executor.execute_tool import parse_function_signature
import pandas as pd
from io import StringIO
from utils import log_msg

DEFOG_API_KEY = "genmab-survival-test"

from connection_manager import ConnectionManager
from db_utils import (
    add_to_recently_viewed_docs,
    get_all_docs,
    get_doc_data,
    get_report_data,
    get_tool_run,
    get_toolboxes,
    store_tool_run,
    update_doc_data,
    update_report_data,
    update_table_chart_data,
    get_table_data,
    get_all_analyses,
    update_tool_run_data,
    delete_doc,
)

from utils import get_metadata

router = APIRouter()

manager = ConnectionManager()

import yaml

with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

dfg_api_key = env["api_key"]

report_assets_dir = env["report_assets_dir"]


# this is an init endpoint that sends things like metadata, glossary, etc
# (basically everything stored in the redis server)
# to the front end
@router.post("/get_user_metadata")
async def get_user_metadata(request: Request):
    """
    Send the metadata, glossary, etc to the front end.
    """
    try:
        metadata_dets = get_metadata()
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
        api_key = data.get("api_key")
        doc_id = data.get("doc_id")

        if username is None or type(username) != str:
            return {"success": False, "error_message": "Invalid username."}

        if api_key is None or type(api_key) != str:
            return {"success": False, "error_message": "Invalid api key."}

        if doc_id is None or type(doc_id) != str:
            return {"success": False, "error_message": "Invalid document id."}

        await add_to_recently_viewed_docs(
            username=username,
            api_key=api_key,
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
            if err:
                return {"success": False, "error_message": err}

            metadata_dets = get_metadata()
            glossary = metadata_dets["glossary"]
            client_description = metadata_dets["client_description"]
            table_metadata_csv = metadata_dets["table_metadata_csv"]

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
                # print("New data: ", new_data)
                if new_data and type(new_data) == dict:
                    if reran_id:
                        print("Reran step: ", reran_id)
                        await manager.send_personal_message(
                            {
                                "success": True,
                                "tool_run_id": reran_id,
                                "tool_run_data": new_data,
                            },
                            websocket,
                        )
                    elif new_data.get("pre_tool_run_message"):
                        print(
                            f"Starting rerunning of step: {new_data.get('pre_tool_run_message')}"
                        )
                        await manager.send_personal_message(
                            {
                                "pre_tool_run_message": new_data.get(
                                    "pre_tool_run_message"
                                ),
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


# setup an analyse_data websocket endpoint
@router.websocket("/analyse_data")
async def analyse_data_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
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

            async for chunk in analyse_data(data.get("question"), df):
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
        print(data)
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

        if inputs is None or type(inputs) != list:
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

        tool = tool_name_dict[tool_name]

        fn = tool["fn"]

        new_tool_run_id = str(uuid4())

        # a new empty step
        new_step = {
            "tool_name": tool_name,
            "model_generated_inputs": inputs,
            "inputs": inputs,
            "function_signature": parse_function_signature(
                inspect.signature(fn).parameters, tool_name
            ),
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
                "code_str": inspect.getsource(fn) if not tool.get("no_code") else None,
            },
            skip_step_update=True,
        )

        if not store_result["success"]:
            return store_result

        # update report data
        update_err = update_report_data(analysis_id, "gen_steps", [new_step])

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

            metadata_dets = get_metadata()
            glossary = metadata_dets["glossary"]
            client_description = metadata_dets["client_description"]
            table_metadata_csv = metadata_dets["table_metadata_csv"]

            global_dict = {
                "user_question": analysis_data["user_question"],
                "table_metadata_csv": table_metadata_csv,
                "client_description": client_description,
                "glossary": glossary,
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
