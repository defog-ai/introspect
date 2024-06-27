import airbyte as ab
import pandas as pd
from datetime import datetime
import json
import os

account_id = os.environ["STRIPE_ACCOUNT_ID"]
api_key = os.environ["STRIPE_CLIENT_SECRET"]

source = ab.get_source("source-stripe")
cache = ab.get_default_cache()
source.set_config(
    config={
        "account_id": account_id,
        "client_secret": api_key,
    }
)
source.check()  # check that everything is ok

cache = ab.get_default_cache()
result = source.read(
    cache=cache,
    streams=[
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
    ],
)

# invoices
invoices = cache["invoices"].to_pandas()
invoices = invoices[
    [
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
    ]
].rename(
    columns={
        "customer": "customer_id",
        "subscription": "subscription_id",
        "charge": "charge_id",
    }
)
for col in ["created", "updated", "period_start", "period_end"]:
    invoices[col] = invoices[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )

# customers
customers = cache["customers"].to_pandas()
customers["city"] = customers["address"].apply(
    lambda x: json.loads(x).get("city", None) if pd.notnull(x) else None
)
customers["country"] = customers["address"].apply(
    lambda x: json.loads(x).get("country", None) if pd.notnull(x) else None
)
customers["state"] = customers["address"].apply(
    lambda x: json.loads(x).get("state", None) if pd.notnull(x) else None
)
customers["postal_code"] = customers["address"].apply(
    lambda x: json.loads(x).get("postal_code", None) if pd.notnull(x) else None
)
customers = customers[
    [
        "id",
        "name",
        "delinquent",
        "email",
        "phone",
        "created",
        "updated",
        "city",
        "country",
        "state",
        "postal_code",
    ]
]
for col in ["created", "updated"]:
    customers[col] = customers[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )

# subscriptions
subscriptions = cache["subscriptions"].to_pandas()
subscriptions["plan_id"] = subscriptions["items"].apply(
    lambda x: json.loads(x)["data"][0]["plan"]["id"] if pd.notnull(x) else None
)
subscriptions["product_id"] = subscriptions["items"].apply(
    lambda x: json.loads(x)["data"][0]["plan"]["product"] if pd.notnull(x) else None
)
subscriptions = subscriptions[
    [
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
        "plan_id",
        "product_id",
    ]
].rename(columns={"customer": "customer_id"})
for col in ["start_date", "ended_at", "created", "updated"]:
    subscriptions[col] = subscriptions[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )

# prices
prices = cache["prices"].to_pandas()
prices["recurring_interval"] = prices["recurring"].apply(
    lambda x: json.loads(x).get("interval", None) if pd.notnull(x) else None
)

prices = prices[
    [
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
        "recurring_interval",
    ]
].rename(columns={"product": "product_id"})

for col in ["created", "updated"]:
    prices[col] = prices[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )

# charges
charges = cache["charges"].to_pandas()
charges = charges[
    [
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
    ]
].rename(columns={"customer": "customer_id", "subscription": "subscription_id"})
for col in ["created", "updated"]:
    charges[col] = charges[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )

# refunds
refunds = cache["refunds"].to_pandas()
refunds = refunds[
    [
        "id",
        "amount",
        "charge",
        "created",
        "updated",
        "currency",
        "reason",
        "receipt_number",
        "status",
    ]
].rename(columns={"charge": "charge_id"})

# products
for col in ["created", "updated"]:
    refunds[col] = refunds[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )

products = cache["products"].to_pandas()
products = products[
    ["id", "active", "description", "created", "name", "updated", "default_price"]
]

for col in ["created", "updated"]:
    products[col] = products[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )

# payouts
payouts = cache["payouts"].to_pandas()
payouts = payouts[
    [
        "id",
        "amount",
        "created",
        "updated",
        "currency",
        "status",
        "arrival_date",
        "description",
        "reconciliation_status",
    ]
]

for col in ["created", "updated", "arrival_date"]:
    payouts[col] = payouts[col].apply(
        lambda x: datetime.fromtimestamp(x) if pd.notnull(x) else None
    )


db_creds = {
    "user": os.environ["DBUSER"],
    "password": os.environ["DBPASSWORD"],
    "host": os.environ["DBHOST"],
    "port": os.environ["DBPORT"],
    "database": os.environ["DATABASE"],
}

from sqlalchemy import create_engine

print("using postgres as our internal db")
connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
engine = create_engine(connection_uri)

# create the "stripe" schema if it doesn't exist
with engine.connect() as connection:
    connection.execute("CREATE SCHEMA IF NOT EXISTS stripe")

invoices.to_sql("invoices", engine, if_exists="replace", index=False, schema="stripe")
customers.to_sql("customers", engine, if_exists="replace", index=False, schema="stripe")
subscriptions.to_sql(
    "subscriptions", engine, if_exists="replace", index=False, schema="stripe"
)
prices.to_sql("prices", engine, if_exists="replace", index=False, schema="stripe")
charges.to_sql("charges", engine, if_exists="replace", index=False, schema="stripe")
refunds.to_sql("refunds", engine, if_exists="replace", index=False, schema="stripe")
products.to_sql("products", engine, if_exists="replace", index=False, schema="stripe")
payouts.to_sql("payouts", engine, if_exists="replace", index=False, schema="stripe")
