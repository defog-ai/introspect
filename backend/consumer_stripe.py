import asyncio
import functools
import json
import os
import time
from datetime import datetime
from io import StringIO

import airbyte as ab
import pandas as pd
import pika
from db_utils import convert_cols_to_jsonb
from generic_utils import make_request
from utils_imported_data import update_imported_tables, update_imported_tables_db
from utils_logging import LOGGER, save_and_log
from utils_md import convert_data_type_postgres

rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
parameters = pika.ConnectionParameters(host=rabbitmq_host)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Declare a queue
queue_name = "stripe"
channel.queue_declare(queue=queue_name)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
INTERNAL_DB = os.environ.get("INTERNAL_DB", "postgres")
STRIPE_SCHEMA = "stripe"  # schema name to store the stripe data
STREAMS = [
    "customers",
    "persons",
    "accounts",
    "refunds",
    "charges",
    "invoices",
    "payouts",
    "plans",
    "prices",
    "products",
    "subscriptions",
    "transactions",
    "subscription_items",
]

# Specify column names to drop from all streams
COLS_TO_DROP = [
    "_airbyte_raw_id",
    "_airbyte_raw_id",
    "_airbyte_meta",
    "_airbyte_extracted_at",
]
# Leave empty to include all columns. Otherwise specify key-value pairs of stream name and list of columns to include.
COLS_IN_STREAMS = {
    "customers": [
        "id",
        "name",
        "delinquent",
        "email",
        "phone",
        "created",
        "updated",
        "address",
    ],
    "refunds": [
        "id",
        "amount",
        "charge",
        "created",
        "updated",
        "currency",
        "reason",
        "receipt_number",
        "status",
    ],
    "charges": [
        "id",
        "failure_message",
        "status",
        "currency",
        "created",
        "updated",
        "refunded",
        "receipt_number",
        "paid",
        "invoice",
        "amount",
        "customer",
        "payment_method",
    ],
    "invoices": [
        "id",
        "created",
        "updated",
        "charge",
        "receipt_number",
        "attempt_count",
        "amount_paid",
        "hosted_invoice_url",
        "period_start",
        "period_end",
        "amount_remaining",
        "number",
        "billing_reason",
        "ending_balance",
        "attempted",
        "invoice_pdf",
        "customer",
        "amount_due",
        "currency",
        "total",
        "subscription",
        "total_excluding_tax",
    ],
    "payouts": [
        "id",
        "amount",
        "created",
        "updated",
        "currency",
        "status",
        "arrival_date",
        "description",
        "reconciliation_status",
    ],
    "prices": [
        "id",
        "active",
        "billing_scheme",
        "created",
        "updated",
        "currency",
        "product",
        "type",
        "unit_amount",
        "is_deleted",
    ],
    "subscriptions": [
        "id",
        "start_date",
        "ended_at",
        "customer",
        "status",
        "created",
        "updated",
        "trial_start",
        "trial_end",
        "collection_method",
        "latest_invoice",
        "items",
    ],
}

# Leave empty to keep column names as is. Otherwise specify key-value pairs of stream name and dictionary mapping old column name to new column name.
RENAMED_COLS = {
    "refunds": {"charge": "charge_id"},
    "charges": {"customer": "customer_id", "subscription": "subscription_id"},
    "invoices": {
        "customer": "customer_id",
        "subscription": "subscription_id",
        "charge": "charge_id",
    },
    "prices": {"product": "product_id"},
    "subscriptions": {"customer": "customer_id"},
}

# Specify names of columns not containing 'date' that should be converted to datetime type
DATE_COLS = [
    "created",
    "updated",
    "period_start",
    "period_end",
    "trial_start",
    "trial_end",
    "ended_at",
]

# Specify key-value pairs of stream name and list of columns that are json columns to be converted to dict type
JSON_COLS = {
    "customers": ["address"],
    "subscriptions": ["items"],
}


def get_stripe_data(
    stripe_account_id: str,
    stripe_client_secret: str,
    data_start_date: str = "1900-01-01",
) -> dict:
    try:
        source = ab.get_source(
            "source-stripe",
            install_if_missing=True,
            config={
                "account_id": stripe_account_id,
                "client_secret": stripe_client_secret,
                "start_date": data_start_date,
            },
        )
    except Exception as e:
        LOGGER.error(
            f"Error in creating Stripe source: {str(e)}. Please check that STRIPE_ACCOUNT_ID and STRIPE_CLIENT_SECRET are set correctly."
        )
        return {"error": str(e)}

    try:
        source.check()
    except Exception as e:
        LOGGER.error(
            f"Error in accessing Stripe data: {str(e)}. Please check that STRIPE_ACCOUNT_ID and STRIPE_CLIENT_SECRET are set correctly."
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
    Process the get_stripe_data queue
    This callback expects the following fields in the payload:
    - api_key: str
    - stripe_account_id: str
    - stripe_client_secret: str
    - data_start_date: str

    The callback will:
    - Get Stripe data from the relevant streams
    - Drop unnecessary columns from the data
    - Parse the data into a dictionary of CSV strings
    - Update the imported_tables database with the new schema and tables
    - Update the imported_tables table entries in the internal db
    - Update the metadata for the api_key in the defog db
    """
    payload = json.loads(body)
    LOGGER.info(f"Received message")
    api_key = payload["api_key"]
    stripe_account_id = payload["stripe_account_id"]
    stripe_client_secret = payload["stripe_client_secret"]
    data_start_date = payload["data_start_date"]

    try:
        ts, timings = time.time(), []
        csv_dict = get_stripe_data(
            stripe_account_id, stripe_client_secret, data_start_date
        )
        save_and_log(ts, "Retrieved stripe data", timings)
    except Exception as e:
        LOGGER.error(f"Error in getting Stripe data: {str(e)}")
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

        # create new columns from json columns
        if table_name == "subscriptions":
            df["plan_id"] = df["items"].apply(
                lambda x: x["data"][0]["plan"]["id"] if pd.notnull(x) else None
            )
            df["product_id"] = df["items"].apply(
                lambda x: x["data"][0]["plan"]["product"] if pd.notnull(x) else None
            )
            # drop items column
            df = df.drop(columns=["items"])
        elif table_name == "customers":
            df["city"] = df["address"].apply(
                lambda x: x.get("city", None) if pd.notnull(x) else None
            )
            df["country"] = df["address"].apply(
                lambda x: x.get("country", None) if pd.notnull(x) else None
            )
            df["state"] = df["address"].apply(
                lambda x: x.get("state", None) if pd.notnull(x) else None
            )
            df["postal_code"] = df["address"].apply(
                lambda x: x.get("postal_code", None) if pd.notnull(x) else None
            )
            # drop address column
            df = df.drop(columns=["address"])

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
        link = "stripe"
        success, old_table_name = update_imported_tables_db(
            link, table_index, table_name, csv_data, STRIPE_SCHEMA
        )
        if not success:
            LOGGER.error(
                f"Error in updating imported tables database for table {table_name}"
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        schema_table_name = f"{STRIPE_SCHEMA}.{table_name}"
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
            convert_cols_to_jsonb(table_name, jsonb_cols, STRIPE_SCHEMA)

        # update imported_tables table entries in internal db
        update_imported_tables(
            link, table_index, old_table_name, schema_table_name, table_description=None
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
            {
                "api_key": api_key,
                "table_metadata": md,
                "db_type": INTERNAL_DB,
                "imported": True,
            },
        )
        if response.get("status") == "success":
            LOGGER.info(
                f"Updated metadata for api_key {api_key}-imported with stripe data"
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
