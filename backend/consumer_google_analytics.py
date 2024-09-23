import json
import os
import time
import asyncio
import functools
import airbyte as ab
import pandas as pd
from datetime import datetime
import pika
import csv
from io import StringIO
from utils_logging import LOGGER, save_and_log
from utils_md import convert_data_type_postgres
from db_utils import (
    update_imported_tables_db,
    update_imported_tables,
    convert_cols_to_jsonb,
)
from generic_utils import make_request


rabbitmq_host = os.environ.get("RABBITMQ_HOST", "agents-rabbitmq")
parameters = pika.ConnectionParameters(host=rabbitmq_host)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Declare a queue
queue_name = "google_analytics"
channel.queue_declare(queue=queue_name)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
INTERNAL_DB = os.environ.get("INTERNAL_DB", "postgres")
STREAMS = [
    "pages",
    "traffic_sources",
    "events_report",
    "locations",
    "devices",
    "daily_active_users",
    "weekly_active_users",
    "four_weekly_active_users",
    "website_overview",
    "pages_path_report",
    "demographic_country_report",
    "demographic_age_report",
    "tech_browser_report",
]

# Specify column names to drop from all streams
COLS_TO_DROP = [
    "_airbyte_raw_id",
    "_airbyte_raw_id",
    "_airbyte_meta",
    "property_id",
    "_airbyte_extracted_at",
]
# Leave empty to include all columns. Otherwise specify key-value pairs of stream name and list of columns to include.
COLS_IN_STREAMS = {}

# Leave empty to keep column names as is. Otherwise specify key-value pairs of stream name and dictionary mapping old column name to new column name.
RENAMED_COLS = {}

# Specify names of columns not containing 'date' that should be converted to datetime type
DATE_COLS = []

# Specify key-value pairs of stream name and list of columns that are json columns to be converted to dict type
JSON_COLS = {}


def get_google_analytics_data(
    ga_property_ids: list, ga_creds_content: dict, data_start_date: str = "1900-01-01"
) -> dict:
    try:
        source = ab.get_source(
            "source-google-analytics-data-api",
            install_if_missing=True,
            config={
                "property_ids": ga_property_ids,
                "credentials": {
                    "credentials_json": json.dumps(ga_creds_content),
                    "auth_type": "Service",
                },
                "date_ranges_start_date": data_start_date,
            },
        )
    except Exception as e:
        LOGGER.error(
            f"Error in creating Google Analytics source: {str(e)}. Please check that GOOGLE_ANALYTICS_CREDS_PATH and GOOGLE_ANALYTICS_PROPERTY_IDS are set correctly."
        )
        return {"error": str(e)}

    try:
        source.check()
    except Exception as e:
        LOGGER.error(
            f"Error in accessing Google Analytics data: {str(e)}. Please check that GOOGLE_ANALYTICS_CREDS_PATH and GOOGLE_ANALYTICS_PROPERTY_IDS are set correctly."
        )
        return {"error": str(e)}

    cache = ab.get_default_cache()
    source.select_streams(STREAMS)
    result = source.read(cache=cache)

    csv_dict = {}
    # clean all streams
    for stream in STREAMS:
        df = cache.get_pandas_dataframe(stream)
        if stream in COLS_IN_STREAMS:
            try:
                df = df[COLS_IN_STREAMS[stream]]
            except KeyError as e:
                LOGGER.error(
                    f"Error in getting columns for stream {stream}: {str(e)}\nExisting columns: {df.columns}"
                )
        if stream in RENAMED_COLS:
            df = df.rename(columns=RENAMED_COLS[stream])
        if df.empty:
            LOGGER.info(f"Empty dataframe for stream: {stream}")
            continue
        existing_cols_to_drop = [col for col in COLS_TO_DROP if col in df.columns]
        df = df.drop(columns=existing_cols_to_drop)
        csv_dict[stream] = df.to_csv(index=False)

    return csv_dict


def sync(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))

    return wrapper


@sync
async def callback(ch, method, properties, body):
    """
    Process the get_google_analytics_data queue
    This callback expects the following fields in the payload:
    - api_key: str
    - ga_property_ids: list
    - ga_creds_content: dict
    - data_start_date: str

    The callback will:
    - Get Google Analytics data from the relevant streams
    - Drop unnecessary columns from the data
    - Parse the data into a dictionary of CSV strings
    - Update the imported_tables database with the new schema and tables
    - Update the imported_tables table entries in the internal db
    - Update the metadata for the api_key in the defog db
    """
    payload = json.loads(body)
    LOGGER.info(f"Received message")
    api_key = payload["api_key"]
    ga_property_ids = payload["ga_property_ids"]
    ga_creds_content = payload["ga_creds_content"]
    data_start_date = payload["data_start_date"]

    try:
        ts, timings = time.time(), []
        csv_dict = get_google_analytics_data(
            ga_property_ids, ga_creds_content, data_start_date
        )
        save_and_log(ts, "Retrieved google analytics data", timings)
    except Exception as e:
        LOGGER.error(f"Error in getting Google Analytics data: {str(e)}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    if not csv_dict:
        LOGGER.info("No data retrieved")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    inserted_tables = {}
    for table_index, (table_name, csv_data) in enumerate(csv_dict.items()):
        # read csv data into a pandas dataframe
        df = pd.read_csv(StringIO(csv_data))

        for col in df.columns:
            # convert date columns to datetime
            if "date" in col or col in DATE_COLS:
                # check if column is string or int type
                try:
                    if "int" in str(df[col].dtype):
                        LOGGER.info(
                            f"Converting date of integer column `{col}` to datetime"
                        )
                        df[col] = df[col].apply(
                            lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else x
                        )
                    elif "object" in str(df[col].dtype):
                        LOGGER.info(
                            f"Converting date of string type column `{col}` to datetime"
                        )
                        df[col] = pd.to_datetime(df[col], format="%Y%m%d")
                except Exception as e:
                    LOGGER.error(f"Error in converting date column {col}: {str(e)}")
                    continue
            # convert json columns to dict
            elif col in JSON_COLS.get(table_name, []):
                LOGGER.info(f"Converting json column `{col}` to dict")
                df[col] = df[col].apply(
                    lambda x: json.loads(x) if pd.notnull(x) else None
                )

        # get data types of columns
        data_types = {}
        for col in df.columns:
            if df[col].dtype == "object":
                first_non_null = df[col].dropna().iloc[0]
                if isinstance(first_non_null, str):
                    data_types[col] = "string"
                elif isinstance(first_non_null, dict):
                    data_types[col] = "jsonb"
                    # convert dict back to json string for insertion into db
                    df[col] = df[col].apply(
                        lambda x: json.dumps(x) if pd.notnull(x) else None
                    )
                else:
                    data_types[col] = type(first_non_null).__name__
            else:
                data_types[col] = df[col].dtype.name
        LOGGER.info(f"Data types:{data_types}")

        data_types_list = [data_types[col] for col in df.columns]
        if INTERNAL_DB == "postgres":
            data_types_list = [
                convert_data_type_postgres(dtype) for dtype in data_types_list
            ]
        else:
            LOGGER.error(
                f"Conversion of data types currently only supported for postgres. Received data types: {data_types_list}"
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # convert df to list of lists by row with headers as the first list
        csv_data = df.values.tolist()
        csv_data.insert(0, df.columns.tolist())

        # update imported_tables database with the ga schema and tables
        schema_name = "ga"
        link = "google_analytics"
        update_imported_tables_db(link, table_index, table_name, csv_data, schema_name)
        schema_table_name = f"{schema_name}.{table_name}"
        inserted_tables[schema_table_name] = [
            {"data_type": data_type, "column_name": col_name, "column_description": ""}
            for data_type, col_name in zip(data_types_list, df.columns)
        ]

        # convert inserted JSON columns in imported_tables database to jsonb type
        jsonb_cols = JSON_COLS.get(table_name, [])
        if jsonb_cols:
            jsonb_cols = [
                col for col in jsonb_cols if col in df.columns
            ]  # only convert columns that exist in the dataframe
            convert_cols_to_jsonb(table_name, jsonb_cols, schema_name)

        # update imported_tables table entries in internal db
        update_imported_tables(
            link, table_index, schema_table_name, table_description=None
        )

    # get and update metadata for {api_key}-imported
    try:
        response = await make_request(
            DEFOG_BASE_URL + "/get_metadata", {"api_key": api_key, "imported": True}
        )
    except Exception as e:
        LOGGER.error(f"Error in getting metadata for api_key {api_key}: {str(e)}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return
    md = response.get("table_metadata", {})
    md.update(inserted_tables)

    try:
        response = await make_request(
            DEFOG_BASE_URL + "/update_metadata",
            {"api_key": api_key, "table_metadata": md, "imported": True},
        )
        if response.get("status") == "success":
            LOGGER.info(
                f"Updated metadata for api_key {api_key}-imported with google analytics data"
            )
        else:
            LOGGER.error(
                f"Error in updating metadata for api_key {api_key}: {response}"
            )
    except Exception as e:
        LOGGER.error(f"Error in updating metadata for api_key {api_key}: {str(e)}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=False,
)

print(f" [*] Waiting for messages in the {queue_name} queue...", flush=True)
channel.start_consuming()
