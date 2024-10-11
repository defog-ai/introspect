import json
import os
from datetime import datetime
from typing import Optional

from db_utils import ORACLE_ENABLED, validate_user
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from generic_utils import get_api_key_from_key_name
from pydantic import BaseModel, Field
from utils_queue import publish

router = APIRouter()

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
if ORACLE_ENABLED:
    os.environ["RABBITMQ_PORT"] = "15672"


class DataConnectorRequest(BaseModel):
    """
    Request body for data connector endpoints.
    """

    key_name: str
    token: str
    data_start_date: Optional[str] = Field(
        default="1900-01-01", description="Start date for data retrieval"
    )


@router.post("/connector/get_google_analytics_data")
async def get_google_analytics_data(request: DataConnectorRequest):
    """
    Connect to Google Analytics, retrieve data and store in imported_tables in the database.
    """
    key_name = request.key_name
    token = request.token
    data_start_date = request.data_start_date
    ga_creds_path = os.environ.get("GOOGLE_ANALYTICS_CREDS_PATH", None)
    ga_property_ids = os.environ.get("GOOGLE_ANALYTICS_PROPERTY_IDS", None)
    username = validate_user(token, user_type=None, get_username=True)
    api_key = get_api_key_from_key_name(key_name)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    if not ga_creds_path:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "GOOGLE_ANALYTICS_CREDS_PATH env var not set",
            },
        )
    if not ga_property_ids:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "GOOGLE_ANALYTICS_PROPERTY_IDS env var not set",
            },
        )
    else:
        ga_property_ids = ga_property_ids.split(",")
    if not os.environ.get("RABBITMQ_HOST"):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "RABBITMQ_HOST env var not set",
            },
        )
    # check that the data_start_date is in the correct format YYYY-MM-DD
    try:
        datetime.strptime(data_start_date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "data_start_date must be in the format YYYY-MM-DD",
            },
        )
    body = {}
    body["api_key"] = api_key
    body["ga_property_ids"] = ga_property_ids
    body["data_start_date"] = data_start_date

    try:
        with open(ga_creds_path, "r") as f:
            ga_creds_content = json.load(f)
    except FileNotFoundError:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "GOOGLE_ANALYTICS_CREDS_PATH file not found",
            },
        )
    body["ga_creds_content"] = ga_creds_content

    publish("google_analytics", json.dumps(body))

    return JSONResponse(
        content={
            "status": "success",
            "message": "Request sent to `google_analytics` queue",
        },
        status_code=200,
    )


@router.post("/connector/get_stripe_data")
async def get_stripe_data(request: DataConnectorRequest):
    """
    Connect to Stripe, retrieve data and store in imported_tables in the database.
    """
    key_name = request.key_name
    token = request.token
    data_start_date = request.data_start_date
    stripe_account_id = os.environ.get("STRIPE_ACCOUNT_ID", None)
    stripe_client_secret = os.environ.get("STRIPE_CLIENT_SECRET", None)
    username = validate_user(token, user_type=None, get_username=True)
    api_key = get_api_key_from_key_name(key_name)
    if not username:
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Invalid username or password",
            },
        )
    if not stripe_account_id:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "STRIPE_ACCOUNT_ID env var not set",
            },
        )
    if not stripe_client_secret:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "STRIPE_CLIENT_SECRET env var not set",
            },
        )
    if not os.environ.get("RABBITMQ_HOST"):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "RABBITMQ_HOST env var not set",
            },
        )
    if not os.environ.get("RABBITMQ_PORT"):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server Error",
                "message": "RABBITMQ_PORT env var not set",
            },
        )
    # check that the data_start_date is in the correct format YYYY-MM-DD
    try:
        datetime.strptime(data_start_date, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": "data_start_date must be in the format YYYY-MM-DDThh:mm:ssZ",
            },
        )
    body = {}
    body["api_key"] = api_key
    body["stripe_account_id"] = stripe_account_id
    body["stripe_client_secret"] = stripe_client_secret
    body["data_start_date"] = data_start_date

    publish("stripe", json.dumps(body))

    return JSONResponse(
        content={
            "status": "success",
            "message": "Request sent to `stripe` queue",
        },
        status_code=200,
    )