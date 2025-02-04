import logging
import os
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import doc_endpoints

from db_utils import (
    ORACLE_ENABLED,
    get_analysis_data,
    initialise_analysis,
)
from generic_utils import get_api_key_from_key_name
import integration_routes, query_routes, admin_routes, auth_routes, readiness_routes, csv_routes, feedback_routes, slack_routes, agent_routes, imgo_routes, user_history_routes, oracle_report_routes

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(integration_routes.router)
app.include_router(query_routes.router)
app.include_router(admin_routes.router)
app.include_router(auth_routes.router)
app.include_router(readiness_routes.router)
app.include_router(doc_endpoints.router)
app.include_router(csv_routes.router)
app.include_router(feedback_routes.router)
app.include_router(imgo_routes.router)
app.include_router(slack_routes.router)
app.include_router(agent_routes.router)
app.include_router(user_history_routes.router)
if ORACLE_ENABLED:
    import oracle_routes, imported_tables_routes, xdb_routes, oracle_report_routes

    app.include_router(imported_tables_routes.router)
    app.include_router(oracle_routes.router)
    app.include_router(xdb_routes.router)
    app.include_router(oracle_report_routes.router)
    from oracle.setup import setup_dir

    # check if the oracle directory structure exists and create if not
    setup_dir(os.getcwd())


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

request_types = ["clarify", "understand", "gen_steps", "gen_analysis"]
llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")




@app.get("/ping")
async def root():
    return {"message": "Hello World"}


edit_request_types_and_prop_names = {
    "edit_analysis_md": {
        "table_column": "gen_analysis",
        "prop_name": "analysis_sections",
    },
    "edit_approaches": {"table_column": "gen_approaches", "prop_name": "approaches"},
}


@app.post("/get_analysis")
async def one_analysis(request: Request):
    try:
        params = await request.json()
        analysis_id = params.get("analysis_id")

        print("get_one_analysis", params)

        err, analysis_data = await get_analysis_data(analysis_id)

        if err is not None:
            return {"success": False, "error_message": err}

        return {"success": True, "analysis_data": analysis_data}
    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"success": False, "error_message": "Incorrect request"}


@app.post("/create_analysis")
async def create_analysis(request: Request):
    try:
        params = await request.json()
        token = params.get("token")

        key_name = params.get("key_name")
        api_key = get_api_key_from_key_name(key_name)

        print("create_analysis", params)

        err, analysis_data = await initialise_analysis(
            user_question="",
            token=token,
            api_key=api_key,
            custom_id=params.get("custom_id"),
            other_initialisation_details=params.get(
                "initialisation_details",
                params.get(
                    "other_data",
                ),
            ),
        )

        if err is not None:
            return {"success": False, "error_message": err}

        return {"success": True, "analysis_data": analysis_data}
    except Exception as e:
        print(e)
        return {"success": False, "error_message": "Incorrect request"}


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/get_api_key_names")
async def get_api_key_names(request: Request):
    DEFOG_API_KEY_NAMES = os.environ.get("DEFOG_API_KEY_NAMES")
    api_key_names = DEFOG_API_KEY_NAMES.split(",")
    return {"api_key_names": api_key_names}
