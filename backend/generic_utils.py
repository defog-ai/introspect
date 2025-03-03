import copy
import re
from datetime import datetime

import httpx
import sqlparse
from db_utils import get_db_names
from utils_logging import LOG_LEVEL, LOGGER, truncate_obj


async def make_request(url, data, timeout=180, log_time=False):
    start_time = datetime.now()
    if LOG_LEVEL == "DEBUG":
        LOGGER.debug(f"Making request to: {url}")
        # avoid excessively long logs (e.g. for base64 encoded images)
        data_copy = copy.deepcopy(data)
        data_str = truncate_obj(data_copy)
        LOGGER.debug(f"Request body:\n{data_str}")
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.post(
            url,
            json=data,
            timeout=timeout,
        )
    response = r.json()
    response_str = truncate_obj(response)
    if log_time:
        LOGGER.info(
            f"Request to {url} took: {(datetime.now() - start_time).total_seconds()}s"
        )

    if r.status_code != 200:
        LOGGER.error(f"Error in request:\n{response_str}")
        return response
    LOGGER.debug(f"Response:\n{response_str}")
    return response


def convert_nested_dict_to_list(table_metadata):
    """
    Convert a nested dictionary of table metadata to a list of dictionaries.
    """
    metadata = []
    # get sorted keys (table names)
    # we sort the keys to ensure consistent ordering of the metadata in the UI
    # without this, the ordering can be inconsistent - making it hard for users to find a specific table
    sorted_keys = sorted(table_metadata.keys())
    for key in sorted_keys:
        table_name = key
        for item in table_metadata[key]:
            item["table_name"] = table_name
            if "column_description" not in item:
                item["column_description"] = ""
            metadata.append(item)
    return metadata


async def get_api_key_from_key_name(key_name):
    db_names = await get_db_names()
    api_key = None
    if key_name in db_names:
        api_key = key_name

    return api_key


def format_sql(sql):
    """
    Formats SQL query to be more readable
    """
    return sqlparse.format(sql, reindent_aligned=True)


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


def is_sorry(sql: str) -> bool:
    """
    Check if the SQL query is a sorry query
    """
    return "sorry" in sql.lower()
