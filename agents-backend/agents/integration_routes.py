from fastapi import APIRouter, Request
from defog import Defog
import redis  # use redis for caching – atleast for now
import json
import pandas as pd
from io import StringIO
from auth_utils import validate_user
import yaml

env = None
with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

redis_host = env["redis_server_host"]

redis_client = redis.Redis(host=redis_host, port=6379, db=0)
router = APIRouter()

DEFOG_API_KEY = "rishabh"


@router.post("/integration/status")
async def status(request: Request):
    """
    This returns the status of the integration.
    Can be one of the following:
    - not_initiated
    - gave_credentials
    - selected_tables
    - got_metadata
    - edited_metadata
    - updated_glossary
    - updated_golden_queries
    - gave_feedback
    """
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}
    status = redis_client.get(f"integration:status")
    return {"status": status}


@router.post("/integration/generate_tables")
async def generate_tables(request: Request):
    params = await request.json()

    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    tables = redis_client.get(f"integration:tables")
    if tables:
        tables = json.loads(tables)
        return {"tables": tables}
    else:
        api_key = DEFOG_API_KEY
        db_type = params.get("db_type")
        db_creds = params.get("db_creds")

        # make username into user key for defog to work
        db_creds["user"] = db_creds["username"]

        # once this is done, we do not have to persist the db_creds
        # since they are already stored in the Defog connection string at ~/.defog/connection.json
        defog = Defog(api_key, db_type, db_creds)
        table_names = defog.generate_db_schema(return_tables_only=True)
        redis_client.set(f"integration:status", "selected_tables")
        redis_client.set(f"integration:status", "gave_credentials")
        redis_client.set(f"integration:tables", json.dumps(table_names))
        redis_client.set(f"integration:db_type", db_type)
        redis_client.set(f"integration:db_creds", json.dumps(db_creds))
        return {"tables": tables}


@router.post("/integration/get_tables_db_creds")
async def get_tables_db_creds(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    tables = redis_client.get(f"integration:tables")
    db_type = redis_client.get(f"integration:db_type")
    db_creds = redis_client.get(f"integration:db_creds")
    if tables:
        tables = json.loads(tables)
        db_creds = json.loads(db_creds)
        return {"tables": tables, "db_type": db_type, "db_creds": db_creds}
    else:
        return {"error": "no tables found"}


@router.post("/integration/generate_metadata")
async def generate_metadata(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    tables = params.get("tables", None)
    if not tables:
        return {"error": "no tables selected"}

    defog = Defog()
    if defog.db_creds is None:
        return {
            "error": "you must first provide the database credentials before this step"
        }
    table_metadata = defog.generate_db_schema(tables=tables, scan=True, upload=True)
    metadata = table_metadata
    redis_client.set(f"integration:status", "edited_metadata")
    redis_client.set(f"integration:metadata", metadata)
    return {"metadata": metadata}


@router.post("/integration/get_metadata")
async def get_metadata(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    metadata = redis_client.get("integration:metadata")
    if metadata:
        metadata = pd.read_csv(StringIO(metadata)).to_dict(orient="records")
        return {"metadata": metadata}
    else:
        return {"error": "no metadata found"}


@router.post("/integration/update_metadata")
async def update_metadata(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    metadata = params.get("metadata", None)
    if not metadata:
        return {"error": "no metadata provided"}

    metadata = pd.DataFrame(metadata).to_csv(index=False)

    redis_client.set(f"integration:status", "updated_metadata")
    redis_client.set(f"integration:metadata", metadata)
    return {"status": "success"}
