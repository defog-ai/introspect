import asyncio
import json
import os

import pandas as pd
from auth_utils import validate_user_request
from db_utils import get_db_type_creds
from defog import Defog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from generic_utils import convert_nested_dict_to_list
from request_models import (
    MetadataGenerateRequest,
    MetadataGetRequest,
    MetadataUpdateRequest,
    TableDescription,
    TableDescriptionsUpdateRequest,
    UserRequest,
)
from utils_instructions import get_instructions
from utils_join_hints import ReasonedJoinHints, get_join_hints
from utils_logging import LOGGER
from utils_md import check_metadata_validity, get_metadata, set_metadata
from utils_table_descriptions import (
    delete_table_descriptions,
    get_all_table_descriptions,
    infer_table_descriptions,
    update_table_descriptions,
)

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Metadata Management"],
)

home_dir = os.path.expanduser("~")
defog_path = os.path.join(home_dir, ".defog")


@router.post("/integration/get_metadata")
async def get_metadata_route(req: MetadataGetRequest):
    """
    Get metadata for a given API key.
    """
    format = req.format
    try:
        metadata = await get_metadata(req.db_name)
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
    """
    # convert metadata to list of dicts
    metadata = [col.model_dump() for col in req.metadata]
    # validate the metadata
    db_type, _ = await get_db_type_creds(req.db_name)
    md_error = check_metadata_validity(metadata, db_type)
    if md_error:
        return JSONResponse(status_code=400, content={"error": md_error})
    try:
        await set_metadata(req.db_name, metadata)
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
    db_name = req.db_name
    res = await get_db_type_creds(req.db_name)
    if res:
        db_type, db_creds = res
    else:
        return {"error": "no db creds found"}

    tables = req.tables

    # see comment in `get_tables_db_creds` for the full context
    selected_tables_path = os.path.join(defog_path, f"selected_tables_{db_name}.json")
    with open(selected_tables_path, "w") as f:
        json.dump(tables, f)

    # this just generates a list of tables
    # no upload or scan, so api_key can be any value and does not matter
    defog = Defog(api_key=db_name, db_type=db_type, db_creds=db_creds)

    metadata_dict = await asyncio.to_thread(
        defog.generate_db_schema,
        tables=tables,
        upload=False,
        scan=False,
    )
    metadata = convert_nested_dict_to_list(metadata_dict)
    LOGGER.debug(f"Generated {len(metadata)} metadata entries")
    return {"metadata": metadata}


@router.post("/integration/get_table_descriptions")
async def get_table_descriptions(req: UserRequest) -> list[TableDescription]:
    """
    Get table descriptions for a given database.
    """
    table_descriptions_list = await get_all_table_descriptions(req.db_name)
    return table_descriptions_list


@router.post("/integration/update_table_descriptions")
async def update_table_descriptions_route(req: TableDescriptionsUpdateRequest) -> None:
    """
    Update table descriptions for a given database.
    """
    try:
        await update_table_descriptions(req.db_name, req.table_descriptions)
    except Exception as e:
        LOGGER.error(f"Error updating table descriptions: {e}")
        return JSONResponse(
            status_code=500, content={"error": "could not update table descriptions"}
        )


@router.post("/integration/delete_table_descriptions")
async def delete_table_descriptions_route(req: UserRequest) -> None:
    """
    Delete table descriptions for a given database.
    """
    await delete_table_descriptions(req.db_name)


@router.post("/integration/generate_table_descriptions")
async def generate_table_descriptions(req: UserRequest) -> list[TableDescription]:
    """
    Query the database for metadata and generate table descriptions.
    """
    metadata = await get_metadata(req.db_name)
    table_descriptions = await infer_table_descriptions(req.db_name, metadata)
    return table_descriptions


@router.post("/integration/get_join_hints")
async def get_join_hints_route(req: UserRequest) -> ReasonedJoinHints:
    """
    Get join hints for a given database.
    """
    metadata = await get_metadata(req.db_name)
    table_descriptions = await get_all_table_descriptions(req.db_name)
    instructions = await get_instructions(req.db_name)
    join_hints = await get_join_hints(req.db_name, metadata, table_descriptions, instructions)
    return join_hints
