import logging
import os
import traceback

import instructions_routes
import admin_routes, agent_routes, auth_routes, csv_routes, doc_endpoints, golden_queries_routes, integration_routes, metadata_routes, oracle_report_routes, query_routes, slack_routes, user_history_routes, imported_tables_routes, oracle_report_routes, oracle_routes, xdb_routes, tools.tool_routes

from db_analysis_utils import get_analysis_data, initialise_analysis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from startup import lifespan

logging.basicConfig(level=logging.INFO)

app = FastAPI(lifespan=lifespan)

app.include_router(admin_routes.router)
app.include_router(agent_routes.router)
app.include_router(auth_routes.router)
app.include_router(csv_routes.router)
app.include_router(doc_endpoints.router)
app.include_router(golden_queries_routes.router)
app.include_router(imported_tables_routes.router)
app.include_router(integration_routes.router)
app.include_router(metadata_routes.router)
app.include_router(oracle_report_routes.router)
app.include_router(oracle_routes.router)
app.include_router(query_routes.router)
app.include_router(slack_routes.router)
app.include_router(tools.tool_routes.router)
app.include_router(user_history_routes.router)
app.include_router(xdb_routes.router)
app.include_router(instructions_routes.router)
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

        db_name = params.get("key_name")
        print("create_analysis", params)

        err, analysis_data = await initialise_analysis(
            user_question="",
            token=token,
            db_name=db_name,
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
