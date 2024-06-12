import httpx


async def make_request(url, json):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            json=json,
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
