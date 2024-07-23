import httpx
import os

DEFOG_API_KEY = os.environ["DEFOG_API_KEY"]  # replace with your DEFOG_API_KEY
DEFOG_API_KEY_NAMES = os.environ.get("DEFOG_API_KEY_NAMES")


async def make_request(url, json):
    print(url)
    print(json, flush=True)
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            json=json,
            timeout=60,
        )

    print(r.content, flush=True)
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
        api_key = DEFOG_API_KEY.split(",")[idx]
    else:
        api_key = DEFOG_API_KEY.split(",")[0]
    return api_key
