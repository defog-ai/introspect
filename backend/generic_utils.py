import httpx
import os
import sqlparse
from datetime import datetime
import re

from utils_logging import LOGGER

DEFOG_API_KEYS = os.environ.get("DEFOG_API_KEYS")
if not DEFOG_API_KEYS:
    DEFOG_API_KEYS = os.environ.get(
        "DEFOG_API_KEY"
    )  # default to old env var for backwards compatibility

    LOGGER.warning(
        f"DEFOG_API_KEYS not set. Defaulting to DEFOG_API_KEY: {DEFOG_API_KEYS}"
    )
DEFOG_API_KEY_NAMES = os.environ.get("DEFOG_API_KEY_NAMES")


async def make_request(url, json):
    print(url)
    print(json, flush=True)
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.post(
            url,
            json=json,
            timeout=60,
        )

    return r.json()


def convert_nested_dict_to_list(table_metadata):
    metadata = []
    for key in table_metadata:
        table_name = key
        for item in table_metadata[key]:
            item["table_name"] = table_name
            if "column_description" not in item:
                item["column_description"] = ""
            metadata.append(item)
    return metadata


def get_api_key_from_key_name(key_name):
    if key_name and key_name in DEFOG_API_KEY_NAMES:
        idx = DEFOG_API_KEY_NAMES.split(",").index(key_name)
        api_key = DEFOG_API_KEYS.split(",")[idx]
    else:
        api_key = DEFOG_API_KEYS.split(",")[0]
    return api_key


def format_sql(sql):
    """
    Formats SQL query to be more readable
    """
    return sqlparse.format(sql, reindent=True, keyword_case="upper")


def format_date_string(iso_date_string):
    """
    Formats date string to be more readable
    """
    if not iso_date_string:
        return ""
    date = datetime.strptime(iso_date_string, "%Y-%m-%dT%H:%M:%S.%f")
    return date.strftime("%Y-%m-%d %H:%M")


def normalize_sql(sql: str) -> str:
    """
    Normalize SQL query string by converting all keywords to uppercase and
    stripping whitespace.
    """
    # remove ; if present first
    if ";" in sql:
        sql = sql.split(";", 1)[0].strip()
    sql = sqlparse.format(
        sql, keyword_case="upper", strip_whitespace=True, strip_comments=True
    )
    # add back ;
    if not sql.endswith(";"):
        sql += ";"
    sql = re.sub(r" cast\(", " CAST(", sql)
    sql = re.sub(r" case when ", " CASE WHEN ", sql)
    sql = re.sub(r" then ", " THEN ", sql)
    sql = re.sub(r" else ", " ELSE ", sql)
    sql = re.sub(r" end ", " END ", sql)
    sql = re.sub(r" as ", " AS ", sql)
    sql = re.sub(r"::float", "::FLOAT", sql)
    sql = re.sub(r"::date", "::DATE", sql)
    sql = re.sub(r"::timestamp", "::TIMESTAMP", sql)
    sql = re.sub(r" float", " FLOAT", sql)
    sql = re.sub(r" date\)", " DATE)", sql)
    sql = re.sub(r" date_part\(", " DATE_PART(", sql)
    sql = re.sub(r" date_trunc\(", " DATE_TRUNC(", sql)
    sql = re.sub(r" timestamp\)", " TIMESTAMP)", sql)
    sql = re.sub(r"to_timestamp\(", "TO_TIMESTAMP(", sql)
    sql = re.sub(r"count\(", "COUNT(", sql)
    sql = re.sub(r"sum\(", "SUM(", sql)
    sql = re.sub(r"avg\(", "AVG(", sql)
    sql = re.sub(r"min\(", "MIN(", sql)
    sql = re.sub(r"max\(", "MAX(", sql)
    sql = re.sub(r"distinct\(", "DISTINCT(", sql)
    sql = re.sub(r"nullif\(", "NULLIF(", sql)
    sql = re.sub(r"extract\(", "EXTRACT(", sql)
    return sql
