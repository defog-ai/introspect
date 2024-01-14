from fastapi import APIRouter, Request
from defog import Defog
import redis # use redis for caching – atleast for now
import json
import pandas as pd
from io import StringIO
from auth_utils import validate_user

redis_client = redis.Redis(host='localhost', port=6379, db=0)
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
        return {
            "error": "unauthorized"
        }
    user_id = params.get("user_id", None)
    status = redis_client.get(f"{user_id}:integration:status")
    return {
        "status": status
    }

@router.post("/integration/get_tables")
async def get_tables(request: Request):
    params = await request.json()
    
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {
            "error": "unauthorized"
        }
    
    user_id = params.get("user_id", None)
    
    tables = redis_client.get(f"{user_id}:integration:tables")
    if tables:
        tables = json.loads(tables)
        return {
            "tables": tables
        }
    else:
        api_key = DEFOG_API_KEY
        db_type = params.get("db_type")
        db_creds = params.get("db_creds")

        # once this is done, we do not have to persist the db_creds
        # since they are already stored in the Defog connection string at ~/.defog/connection.json
        defog = Defog(api_key, db_type, db_creds)
        table_names = defog.generate_db_schema(return_tables_only=True)
        redis_client.set(f"{user_id}:integration:status", "selected_tables")
        redis_client.set(f"{user_id}:integration:status", "gave_credentials")
        redis_client.set(f"{user_id}:integration:tables", json.dumps(table_names))
        return {
            "tables": tables
        }

@router.post("/integration/get_metadata")
async def get_metadata(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {
            "error": "unauthorized"
        }
    
    user_id = params.get("user_id", None)
    tables = params.get("tables", None)
    if not user_id:
        return {
            "error": "unauthorized"
        }
    if not tables:
        return {
            "error": "no tables selected"
        }
    
    if not user_id:
        return {
            "error": "unauthorized"
        }
    
    defog = Defog()
    if defog.db_creds is None:
        return {
            "error": "you must first provide the database credentials before this step"
        }
    table_metadata = defog.generate_db_schema(tables=tables, scan=True, upload=True)
    metadata = pd.read_csv(StringIO(table_metadata)).to_dict(orient="records")
    redis_client.set(f"{user_id}:integration:status", "edited_metadata")
    redis_client.set(f"{user_id}:integration:metadata", json.dumps(metadata))
    return {
        "metadata": metadata
    }

@router.post("/integration/update_metadata")
async def update_metadata(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {
            "error": "unauthorized"
        }
    
    user_id = params.get("user_id", None)
    metadata = params.get("metadata", None)
    if not user_id:
        return {
            "error": "unauthorized"
        }
    if not metadata:
        return {
            "error": "no metadata provided"
        }
    
    redis_client.set(f"{user_id}:integration:status", "updated_metadata")
    redis_client.set(f"{user_id}:integration:metadata", json.dumps(metadata))
    return {
        "status": "success"
    }