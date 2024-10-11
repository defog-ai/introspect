# This script is meant to be run within the backend directory inside the docker
# container, or anywhere the self-hosted postgres database is running.

import requests
import json

base_url = "http://0.0.0.0:1235"

payload = json.dumps(
    {
        "api_key": "123",
        "data": [
            ["product_name", "price", "quantity", "date_purchased", "card_number"],
            ["apple", "1.00", "5", "2021-01-01", "4111111111111111"],
            ["banana", "0.50", "10", "2021-01-02", "378282246310005"],
            ["cherry", "2.00", "3", "2021-01-03", "6011000990139424"],
            ["durian", "5.00", "1", "2021-01-04", "3530111333300000"],
            ["elderberry", "3.00", "2", "2021-01-05", "5555555555554444"],
        ],
        "link": "https://example.com",
        "table_index": 0,
        "table_name": "fruit_products",
        "table_description": "This table contains fruit products purchased by certain card numbers",
    }
)
headers = {"Content-Type": "application/json"}

response = requests.request(
    "POST", f"{base_url}/import_table/create", headers=headers, data=payload
)

print(response.text)
