import asyncio
import json
import os

import pandas as pd
from auth_utils import validate_user_request
from db_utils import get_db_type_creds
from defog import Defog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from generic_utils import (
    convert_nested_dict_to_list,
    get_api_key_from_key_name,
    make_request,
)
from request_models import (
    MetadataGenerateRequest,
    MetadataGetRequest,
    MetadataUpdateRequest,
)
from utils_logging import LOGGER
from utils_md import check_metadata_validity, get_metadata, set_metadata

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Metadata Management"],
)

home_dir = os.path.expanduser("~")
defog_path = os.path.join(home_dir, ".defog")
DEFOG_BASE_URL = os.getenv("DEFOG_BASE_URL")


@router.post("/integration/get_metadata")
async def get_metadata_route(req: MetadataGetRequest):
    """
    Get metadata for a given API key.
    TODO (DEF-720): Get metadata from postgres database using key_name as the api_key
    """
    api_key = get_api_key_from_key_name(req.key_name)
    format = req.format
    try:
        metadata = await get_metadata(api_key)
        if format == "csv":
            # we rely on pd's csv serialization to handle various edge cases
            # like escaping special characters and quotes in the column names
            metadata = pd.DataFrame(metadata)[
                ["table_name", "column_name", "data_type", "column_description"]
            ].to_csv(index=False)
        return {"metadata": metadata}
    except Exception as e:
        LOGGER.error(f"Error getting metadata: {e}")
        return JSONResponse(
            status_code=500, content={"error": "could not get metadata"}
        )


@router.post("/integration/update_metadata")
async def update_metadata_route(req: MetadataUpdateRequest):
    """
    Update metadata for a given API key.
    TODO (DEF-720): Get metadata from postgres database using key_name as the api_key
    """
    api_key = get_api_key_from_key_name(req.key_name)
    # convert metadata to list of dicts
    metadata = [col.model_dump() for col in req.metadata]
    # validate the metadata
    db_type, db_creds = await get_db_type_creds(api_key)
    md_error = check_metadata_validity(metadata, db_type)
    if md_error:
        return JSONResponse(status_code=400, content={"error": md_error})
    try:
        await set_metadata(api_key, metadata)
        return {"success": True}
    except Exception as e:
        LOGGER.error(f"Error updating metadata: {e}")
        return JSONResponse(
            status_code=500, content={"error": "could not update metadata"}
        )


@router.post("/integration/generate_metadata")
async def generate_metadata(req: MetadataGenerateRequest):
    """
    Query the database and generate metadata for the given tables.
    """
    key_name = req.key_name
    api_key = get_api_key_from_key_name(key_name)
    res = await get_db_type_creds(api_key)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    tables = req.tables

    # see comment in `get_tables_db_creds` for the full context
    selected_tables_path = os.path.join(defog_path, f"selected_tables_{api_key}.json")
    with open(selected_tables_path, "w") as f:
        json.dump(tables, f)

    defog = Defog(api_key=api_key, db_type=db_type, db_creds=db_creds)
    defog.base_url = DEFOG_BASE_URL

    metadata_dict = await asyncio.to_thread(
        defog.generate_db_schema,
        tables=tables,
        upload=False,
        scan=False,
    )
    metadata = convert_nested_dict_to_list(metadata_dict)
    LOGGER.debug(f"Generated {len(metadata)} metadata entries")
    return {"metadata": metadata}
