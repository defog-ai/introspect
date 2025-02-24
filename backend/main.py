import logging
import os
import traceback

from db_utils import get_db_names
import instructions_routes
import admin_routes, query_data_routes, auth_routes, file_upload_routes, golden_queries_routes, imported_tables_routes, integration_routes, metadata_routes, oracle_report_routes, oracle_routes, query_routes, slack_routes, tools.tool_routes, user_history_routes, xdb_routes
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from startup import lifespan
from auth_utils import validate_user
from query_data.core_functions import analyse_data_streaming


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("server")

app = FastAPI(lifespan=lifespan)

app.include_router(admin_routes.router)
app.include_router(query_data_routes.router)
app.include_router(auth_routes.router)
app.include_router(file_upload_routes.router)
app.include_router(golden_queries_routes.router)
app.include_router(imported_tables_routes.router)
app.include_router(instructions_routes.router)
app.include_router(integration_routes.router)
app.include_router(metadata_routes.router)
app.include_router(oracle_report_routes.router)
app.include_router(oracle_routes.router)
app.include_router(query_routes.router)
app.include_router(slack_routes.router)
app.include_router(tools.tool_routes.router)
app.include_router(user_history_routes.router)
app.include_router(xdb_routes.router)
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


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/get_db_names")
async def get_db_names_endpoint(request: Request):
    return {"db_names": await get_db_names()}


# setup an analysis data endpoint with streaming and websockets
# moving this here since to avoid dependency injection in `agent_routes.py`
@app.websocket("/analyse_data_streaming")
async def analyse_data_streaming_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data_in = await websocket.receive_json()
        question = data_in.get("question")
        data_csv = data_in.get("data_csv")
        sql = data_in.get("sql")
        auth_token = data_in.get("token")
        validated = await validate_user(auth_token)
        if validated:
            async for token in analyse_data_streaming(
                question=question, data_csv=data_csv, sql=sql
            ):
                await websocket.send_text(token)
        else:
            await websocket.send_text(
                "Invalid authentication. Are you sure you are logged in?"
            )

        # Send a final message to indicate the end of the stream
        await websocket.send_text("Defog data analysis has ended")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        LOGGER.error("Error with websocket connection:" + str(e))
        traceback.print_exc()
    finally:
        await websocket.close()
