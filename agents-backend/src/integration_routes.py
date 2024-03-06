import traceback
from fastapi import APIRouter, Request
from defog import Defog
import redis  # use redis for caching – atleast for now
import json
import pandas as pd
from io import StringIO
from auth_utils import validate_user
import yaml
import asyncio

env = None
with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

redis_host = env["redis_server_host"]

redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
router = APIRouter()

DEFOG_API_KEY = "genmab-survival-test"


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

    api_key = DEFOG_API_KEY
    db_type = params.get("db_type")
    db_creds = params.get("db_creds")

    # remove db_type from db_creds if it exists or sqlalchemy throws an error inside defog
    if "db_type" in db_creds:
        del db_creds["db_type"]

    # once this is done, we do not have to persist the db_creds
    # since they are already stored in the Defog connection string at ~/.defog/connection.json
    defog = Defog(api_key, db_type, db_creds)
    table_names = await asyncio.to_thread(
        defog.generate_db_schema, tables=[], return_tables_only=True
    )
    if "schema" in db_creds:
        table_names = [f"{db_creds['schema']}.{table}" for table in table_names]
    redis_client.set(f"integration:status", "selected_tables")
    redis_client.set(f"integration:status", "gave_credentials")
    redis_client.set(f"integration:tables", json.dumps(table_names))
    redis_client.set(f"integration:db_type", db_type)
    redis_client.set(f"integration:db_creds", json.dumps(db_creds))
    return {"tables": table_names}


@router.post("/integration/get_tables_db_creds")
async def get_tables_db_creds(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    tables = redis_client.get("integration:tables")
    selected_tables = redis_client.get("integration:selected_tables")
    if selected_tables:
        selected_tables = json.loads(selected_tables)
    db_type = redis_client.get("integration:db_type")
    db_creds = redis_client.get("integration:db_creds")
    if tables:
        tables = json.loads(tables)
        db_creds = json.loads(db_creds)
        return {
            "tables": tables,
            "db_type": db_type,
            "db_creds": db_creds,
            "selected_tables": selected_tables,
        }
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

    redis_client.set("integration:selected_tables", json.dumps(tables))

    api_key = DEFOG_API_KEY
    db_type = redis_client.get(f"integration:db_type")
    db_creds = json.loads(redis_client.get(f"integration:db_creds"))

    if db_creds is None:
        return {
            "error": "you must first provide the database credentials before this step"
        }

    try:
        defog = Defog(api_key, db_type, db_creds)

        if "schema" in db_creds:
            schema = db_creds["schema"]
            tables = [table.replace(schema + ".", "") for table in tables]

        table_metadata = await asyncio.to_thread(
            defog.generate_db_schema,
            tables=tables,
            scan=False,
            upload=True,
            return_format="csv_string",
        )

        hard_coded_descriptions = {
            "accession_id": "Unique identifier for each sample or data entry.",
            "well": "The specific location of the sample on the plate, crucial for mapping assay results. Possible values include: A04, A05, A06, A07, A08, A09, A10, A11, A12, B04",
            "plate_sample": "A code that uniquely identifies a sample on its plate.. Possible values include: U001, U002, U009, U017, U025, U033",
            "assay": "Often refers to the name of a cytokine. The type of biochemical assay performed. Possible values include: GM-CSF, Granzyme B, I-TAC, IL-17a, IL-1b, IP-10, MCP-1, PD-1, PD-L1, gp130",
            "signal": "The raw signal output from the assay, indicating the measurement intensity.",
            "mean": "Average signal across replicates or related samples, providing a baseline for comparison.",
            "cv": "Coefficient of Variation, showing the variability of assay results relative to the mean.",
            "calc_concentration": "The calculated concentration of the target in the sample",
            "calc_conc_mean": "The average calculated concentration across samples or replicates. Use for standardizing measurements and providing a baseline",
            "calc_conc_cv": "Coefficient of Variation for the calculated concentrations, assessing precision across measurements.",
            "verified": "Indicates whether the assay result has been verified. Possible values include: PASS, FAIL",
            "sample": "A general identifier or description for the sample.",
            "cohort": "The name of the cohort or group to which the sample belongs, which could be based on study design",
            "study_participant_id": "A unique identifier for the study participant from whom the sample was collected, ensuring privacy and tracking.",
            "visit_timepoint": 'Timepoint of the participant\'s visit when the sample was collected. This is in the format CXDY, where X is the cycle number and Y is the day within that cycle. A "baseline" refers to the visit_timepoint corresponding to C1D1',
            "coc": "Chain of Custody, detailing the sample's handling history to ensure integrity.",
            "status": "The current status of the sample or assay.",
            "disposition": "The outcome or decision regarding the sample's analysis or use.",
            "sample_type": "The type of biological material, providing context for assay interpretation. For example, Tissue",
            "cd": "An abbreviation for a specific department or classification, indicating organizational context. For example, Biomarker Ops",
            "study": "Name or identifier of the study the data pertains to.",
            "pooled": "Indicates whether the sample was part of a pooled set, important for data analysis.",
            "restriction_class": "Describes any restrictions on the sample's use, ensuring compliance with regulations. Possible values: Long Term Sample Retention",
            "location": "The physical or logical location for the sample or data storage, facilitating retrieval and management.",
            "collection_date": "The date when the sample was collected, important for temporal analysis.",
            "project_id": "A unique identifier for the project associated with the data, useful for tracking and management.",
            "sample_list_study_participant_id": "Identifier linking the sample to a study participant.",
            "panel_id": "Identifier for the panel of tests or measurements applied to the sample.",
            "parent_population": "",
            "population": "",
            "variable_name": "Name of the variable. This is generally in the format `PARENT_CELL+/XXX GENE_NAME XXX`, where the PARENT_CELL can be CD4+, CD8+ etc",
            "variable_value": "Value of the measurement named in variable_name.",
            "viability_percentage": "ercentage of viable cells in the sample, if applicable.",
            "original_result_unit_raw": "Original unit of the result before any processing. Possible values: median, percent_parent",
            "original_result_unit": "Unit of the original result. Should generally be ignored when creating queries",
            "readout_type": "Type of readout",
            "parent_cell_count": "Number of parent cells",
            "parent_cell_count_flag": "Flag indicating if parent cell count is present",
            "mfi_reportable_marker": "Reportable marker for MFI",
        }

        table_metadata = pd.read_csv(StringIO(table_metadata)).fillna("")
        table_metadata["column_description"] = table_metadata["column_name"].apply(
            lambda x: hard_coded_descriptions.get(x, x)
        )

        table_metadata["table_name"] = table_metadata["table_name"].apply(
            lambda x: "gmb_gxp_rdap_dev." + schema + "." + x
        )

        metadata = table_metadata.to_dict(orient="records")
        table_metadata = table_metadata.to_csv(index=False)
        redis_client.set(f"integration:status", "edited_metadata")
        redis_client.set(f"integration:metadata", table_metadata)
        return {"metadata": metadata}
    except Exception as e:
        traceback.print_exc()

        return {"error": str(e)}


@router.post("/integration/get_metadata")
async def get_metadata(request: Request):
    params = await request.json()
    token = params.get("token", None)
    if not validate_user(token, user_type="admin"):
        return {"error": "unauthorized"}

    metadata = redis_client.get("integration:metadata")
    if metadata:
        metadata = pd.read_csv(StringIO(metadata)).fillna("").to_dict(orient="records")
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
