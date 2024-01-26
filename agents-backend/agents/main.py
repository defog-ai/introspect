import os
import sys
import traceback
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import FileResponse
from starlette.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from connection_manager import ConnectionManager
from report_data_manager import ReportDataManager
import doc_endpoints
import yaml

from db_utils import (
    get_all_reports,
    get_report_data,
    initialise_report,
    update_report_data,
)
from utils import get_metadata
import integration_routes, admin_routes, auth_routes

manager = ConnectionManager()

app = FastAPI()
app.include_router(integration_routes.router)
app.include_router(admin_routes.router)
app.include_router(auth_routes.router)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

test_resp = {"test": "test"}

request_types = ["clarify", "understand", "gen_approaches", "gen_steps", "gen_report"]


with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

report_assets_dir = env["report_assets_dir"]


app.include_router(doc_endpoints.router)


@app.get("/ping")
async def root():
    return {"message": "Hello World"}


edit_request_types_and_prop_names = {
    "edit_report_md": {"table_column": "gen_report", "prop_name": "report_sections"},
    "edit_approaches": {"table_column": "gen_approaches", "prop_name": "approaches"},
}


@app.post("/edit_report")
async def edit_report(request: Request):
    try:
        params = await request.json()
        if (
            not params.get("request_type")
            or not params.get("request_type") in edit_request_types_and_prop_names
            or not params.get("report_id")
        ):
            return {"success": False, "error_message": "Invalid request"}

        request_type = params["request_type"]
        table_column = edit_request_types_and_prop_names[request_type]["table_column"]
        prop_name = edit_request_types_and_prop_names[request_type]["prop_name"]
        # check if the request has the correct prop name
        if not params.get(prop_name):
            return {"success": False, "error_message": "Invalid request"}

        new_data = params[prop_name]
        report_id = params["report_id"]
        update_report_data(report_id, table_column, new_data, replace=True)
        return {"success": True}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"success": False, "error_message": "An error occurred"}


@app.post("/get_reports")
async def all_reports(request: Request):
    try:
        params = await request.json()
        api_key = params.get("api_key")
        err, reports = get_all_reports(api_key)
        if err is not None:
            return {"success": False, "error_message": err}

        return {"success": True, "reports": reports}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"success": False, "error_message": "Incorrect request"}


@app.post("/get_report")
@app.post("/get_analysis")
async def one_report(request: Request):
    try:
        params = await request.json()
        report_id = params.get("report_id")

        print("get_one_report", params)

        err, report_data = get_report_data(report_id)

        if err is not None:
            return {"success": False, "error_message": err}

        return {"success": True, "report_data": report_data}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"success": False, "error_message": "Incorrect request"}


@app.post("/create_report")
@app.post("/create_analysis")
async def create_report(request: Request):
    try:
        params = await request.json()
        api_key = params.get("api_key")
        username = params.get("username")

        print("create_report", params)

        err, report_data = initialise_report(
            "", api_key, username, params.get("custom_id"), params.get("other_data")
        )

        if err is not None:
            return {"success": False, "error_message": err}

        return {"success": True, "report_data": report_data}
    except Exception as e:
        print(e)
        return {"success": False, "error_message": "Incorrect request"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            try:
                if data.get("ping") is not None:
                    await websocket.send_json({"pong": True})
                    continue

                if "request_type" not in data:
                    await websocket.send_json(
                        {"error_message": "No request type provided"}
                    )
                    continue

                # find request type
                request_type = data.get("request_type")
                if (
                    request_type not in request_types
                    and request_type != "update_report_md"
                ):
                    await websocket.send_json(
                        {"error_message": "Incorrect request type"}
                    )
                    continue

                if "user_question" not in data or data["user_question"] == "":
                    await websocket.send_json(
                        {"error_message": "Please provide a question."}
                    )
                    continue

                report_id = data.get("report_id")

                # start a report data manager
                # this fetches currently existing report data for this report
                report_data_manager = ReportDataManager(
                    data["user_question"],
                    report_id,
                    data.get("db_creds"),
                )

                # if this report is invalid
                if report_data_manager.invalid:
                    await websocket.send_json(
                        {"success": False, "error_message": "Error. Invalid report id?"}
                    )
                    continue

                resp = {}
                resp["request_type"] = request_type
                resp["report_id"] = report_data_manager.report_data["report_id"]

                toolboxes = (
                    data.get("toolboxes")
                    if data.get("toolboxes") and type(data.get("toolboxes")) == list
                    else []
                )
                metadata_dets = get_metadata()
                glossary = metadata_dets["glossary"]
                client_description = metadata_dets["client_description"]
                table_metadata_csv = metadata_dets["table_metadata_csv"]
                # run the agent as per the request_type
                err, agent_output = await report_data_manager.run_agent(
                    report_id=report_id,
                    request_type=request_type,
                    user_question=data["user_question"],
                    client_description=client_description,
                    table_metadata_csv=table_metadata_csv,
                    post_process_data=data,
                    glossary=glossary,
                    # user_email is used to figure out which tools to give to the user
                    user_email=data.get("user_email"),
                    extra_approaches=[],
                    db_creds=data.get("db_creds"),
                    toolboxes=toolboxes,
                )

                # if the agent output is a generator, run it
                if err is None:
                    try:
                        if "generator" in agent_output:
                            g = agent_output["generator"]
                            async for out in g():
                                sys.stdout.flush()
                                # allow our generators to yield None
                                if out is not None:
                                    resp["output"] = {
                                        "success": True,
                                        agent_output["prop_name"]: out,
                                    }
                                    await websocket.send_json(resp)
                                    # update report data in db
                                    report_data_manager.update(request_type, out)

                            # send done true
                            await websocket.send_json(
                                {"done": True, "request_type": request_type}
                            )
                        else:
                            # if not a generator agent
                            resp["output"] = agent_output
                            resp["done"] = True
                            await websocket.send_json(resp)
                            report_data_manager.update(
                                request_type,
                                agent_output,
                                replace=request_type == "gen_report",
                            )
                    except Exception as e:
                        traceback.print_exc()
                        print(e)
                        await websocket.send_json(
                            {
                                "done": True,
                                "success": False,
                                "error_message": "Something went wrong. Please try again or contact us if this persists.",
                            }
                        )

                else:
                    resp["error_message"] = err
                    await websocket.send_json(resp)

            except Exception as e:
                traceback.print_exc()
                print(e)
                await websocket.send(
                    {
                        "success": False,
                        "error_message": "Something went wrong. Please try again or contact us if this persists.",
                    }
                )
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

@app.get("/get_assets")
async def get_assets(path: str):
    try:
        return FileResponse(os.path.join(report_assets_dir, path))
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"success": False, "error_message": "Error getting assets"}