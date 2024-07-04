import os
import traceback
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import FileResponse
from starlette.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from connection_manager import ConnectionManager
from report_data_manager import ReportDataManager
from agents.planner_executor.execute_tool import execute_tool
from agents.planner_executor.planner_executor_agent_rest import RESTExecutor
import doc_endpoints
from uuid import uuid4
from utils import make_request

from db_utils import (
    get_all_reports,
    get_report_data,
    initialise_report,
    update_report_data,
    store_tool_run,
    validate_user,
)
from generic_utils import get_api_key_from_key_name
import integration_routes, query_routes, admin_routes, auth_routes, readiness_routes

manager = ConnectionManager()

app = FastAPI()
app.include_router(integration_routes.router)
app.include_router(query_routes.router)
app.include_router(admin_routes.router)
app.include_router(auth_routes.router)
app.include_router(readiness_routes.router)
app.include_router(doc_endpoints.router)


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


report_assets_dir = os.environ["REPORT_ASSETS_DIR"]


@app.get("/ping")
async def root():
    return {"message": "Hello World"}


edit_request_types_and_prop_names = {
    "edit_report_md": {"table_column": "gen_report", "prop_name": "report_sections"},
    "edit_approaches": {"table_column": "gen_approaches", "prop_name": "approaches"},
}


async def get_classification(question, api_key, debug=False):
    r = await make_request(
        url=f"{os.environ['DEFOG_BASE_URL']}/classify_question",
        payload={"question": question, "api_key": api_key},
    )
    if r.status_code == 200:
        return r.json()
    else:
        print(f"Error getting question classification: {r.status_code}")
        print(r.text)


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
        err = await update_report_data(report_id, table_column, new_data, replace=True)
        if err is not None:
            raise Exception(err)

        return {"success": True}
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
        return {"success": False, "error_message": "An error occurred"}


@app.post("/get_reports")
async def all_reports(request: Request):
    params = await request.json()
    key_name = params.get("key_name")
    api_key = get_api_key_from_key_name(key_name)
    try:
        err, reports = get_all_reports(api_key=api_key)
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
        token = params.get("token")

        key_name = params.get("key_name")
        api_key = get_api_key_from_key_name(key_name)

        print("create_report", params)

        err, report_data = await initialise_report(
            user_question="",
            token=token,
            api_key=api_key,
            custom_id=params.get("custom_id"),
            other_data=params.get("other_data"),
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

                key_name = data.get("key_name")
                api_key = get_api_key_from_key_name(key_name)

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
                token = data.get("token")
                if validate_user(token) is False:
                    await websocket.send_json(
                        {"success": False, "error_message": "Invalid token"}
                    )
                    continue
                dev = data.get("dev")
                temp = data.get("temp")

                # start a report data manager
                # this fetches currently existing report data for this report
                report_data_manager = ReportDataManager(
                    dfg_api_key=api_key,
                    user_question=data["user_question"],
                    report_id=report_id,
                    dev=dev,
                    temp=temp,
                )

                await report_data_manager.async_init()

                # if this report is invalid
                if report_data_manager.invalid:
                    await websocket.send_json(
                        {"success": False, "error_message": "Error. Invalid report id?"}
                    )
                    continue

                resp = {}
                resp["request_type"] = request_type
                resp["analysis_id"] = report_data_manager.report_data["report_id"]

                # if the question has "sqlcoder" in it, we can skip the agent
                # and change the classification to sqlcoder
                if "sqlcoder" in data["user_question"]:
                    print("sqlcoder word found in question")
                    classification = {"prediction": "sqlcoder"}

                elif "agent" in data["user_question"]:
                    print("agent word found in question")
                    classification = {"prediction": "agent"}
                else:
                    # check if the user question needs agents, or just sqlcoder is fine
                    classification = await get_classification(
                        question=data["user_question"], api_key=api_key
                    )

                print(classification, flush=True)
                if classification["prediction"] == "sqlcoder":
                    # first, send the clarifier result as done
                    if request_type == "clarify":
                        resp["output"] = {
                            "success": True,
                            "clarification_questions": [],
                        }
                        # save blank clarifying step to the report data
                        await report_data_manager.update("clarify", [], replace=True)

                        await websocket.send_json(resp)
                        del resp["output"]
                        resp["done"] = True

                    if request_type == "gen_steps":
                        # get the sqlcoder response
                        inputs = {
                            "question": data["user_question"],
                        }
                        result, tool_input_metadata = await execute_tool(
                            function_name="data_fetcher_and_aggregator",
                            tool_function_inputs=inputs,
                            global_dict={
                                "dfg_api_key": api_key,
                                "dev": dev,
                                "temp": temp,
                            },
                        )
                        tool_run_id = str(uuid4())
                        step = {
                            "description": data["user_question"],
                            "tool_name": "data_fetcher_and_aggregator",
                            "inputs": inputs,
                            "outputs_storage_keys": ["answer"],
                            "done": True,
                            "tool_run_id": tool_run_id,
                            "error_message": None,
                            "input_metadata": {
                                "question": {
                                    "name": "question",
                                    "type": "str",
                                    "default": None,
                                    "description": "natural language description of the data required to answer this question (or get the required information for subsequent steps) as a string",
                                }
                            },
                            "model_generated_inputs": inputs,
                        }

                        # save the above step to the report data
                        await report_data_manager.update(
                            "gen_steps", [step], replace=True
                        )

                        # store the tool run of the step
                        store_result = await store_tool_run(
                            resp["analysis_id"], step, result
                        )
                        print(store_result, flush=True)
                        resp["output"] = {
                            "success": True,
                            "steps": [step],
                        }
                        await websocket.send_json(resp)

                        del resp["output"]
                        resp["done"] = True
                        await websocket.send_json(resp)
                else:
                    # if the user question is for the agent
                    toolboxes = (
                        data.get("toolboxes")
                        if data.get("toolboxes") and type(data.get("toolboxes")) == list
                        else []
                    )
                    # run the agent as per the request_type
                    err, agent_output = await report_data_manager.run_agent(
                        report_id=report_id,
                        request_type=request_type,
                        user_question=data["user_question"],
                        post_process_data=data,
                        # token is used to figure out which tools to give to the user
                        token=token,
                        extra_approaches=[],
                        db_creds=data.get("db_creds"),
                        toolboxes=toolboxes,
                        dev=dev,
                        temp=temp,
                    )

                    # if the agent output is a generator, run it
                    if err is None:
                        try:
                            if "generator" in agent_output:
                                g = agent_output["generator"]
                                async for out in g():
                                    # allow our generators to yield None
                                    if out is not None:
                                        resp["output"] = {
                                            "success": True,
                                            agent_output["prop_name"]: out,
                                        }

                                        overwrite_key = getattr(
                                            out, "overwrite_key", None
                                        )
                                        # if the out has an overwrite_key
                                        # update report data in db
                                        await report_data_manager.update(
                                            request_type,
                                            out,
                                            False,
                                            overwrite_key,
                                        )

                                        if overwrite_key:
                                            resp["overwrite_key"] = overwrite_key

                                        await websocket.send_json(resp)

                                # send done true
                                await websocket.send_json(
                                    {
                                        "done": True,
                                        "request_type": request_type,
                                        "analysis_id": report_id,
                                    }
                                )
                            else:
                                # if not a generator agent
                                resp["output"] = agent_output
                                resp["done"] = True
                                await websocket.send_json(resp)
                                await report_data_manager.update(
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
                                    "error_message": str(e)[:300],
                                    "analysis_id": report_id,
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
                        "analysis_id": report_id,
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


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/plan_and_execute")
async def plan_and_execute(request: Request):
    data = await request.json()
    question = data.get("question")
    dev = data.get("dev")
    api_key = data.get("api_key")
    assignment_understanding = data.get("assignment_understanding", "")
    executor = RESTExecutor(
        dfg_api_key=api_key,
        user_question=question,
        assignment_understanding=assignment_understanding,
        dev=dev,
    )
    steps, success = await executor.execute()
    return {"steps": steps, "success": success}
