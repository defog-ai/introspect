from typing import Dict, List
import base64
import os
from generic_utils import make_request
import os
import json

analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")


def encode_image(image_path):
    """
    Encodes an image to base64.
    """
    image_path = os.path.join(analysis_assets_dir, image_path)
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# make sure the query does not contain any malicious commands like drop, delete, etc.
def safe_sql(query):
    if query is None:
        return False

    query = query.lower()
    if (
        "drop" in query
        or "delete" in query
        or "truncate" in query
        or "append" in query
        or "insert" in query
        or "update" in query
        or "create" in query
    ):
        return False

    return True


# resolves an input to a tool
# by replacing global_dict references to the actual variable values
def resolve_input(inp, global_dict):
    # if inp is list, replace each element in the list with call to resolve_input
    if isinstance(inp, list):
        resolved_inputs = []
        for inp in inp:
            resolved_inputs.append(resolve_input(inp, global_dict))

        return resolved_inputs

    elif isinstance(inp, str) and inp.startswith("global_dict."):
        variable_name = inp.split(".")[1]
        print(inp)
        return global_dict.get(variable_name)

    else:
        if isinstance(inp, str):
            # if only numbers, return float
            if inp.isnumeric():
                return float(inp)

            # if None as a string after stripping, return None
            if inp.strip() == "None":
                return None
            return inp

        return inp


async def analyse_data(question: str, data_csv: str, sql: str, api_key: str) -> str:
    """
    Generate a short summary of the results for the given qn.
    """
    if os.environ.get("ANALYZE_DATA", "no") != "yes":
        return ""
    else:
        if os.environ.get("ANALYZE_DATA_MODEL") == "defog":
            analysis = await make_request(
                url=DEFOG_BASE_URL + "/oracle/gen_explorer_data_analysis",
                data={
                    "api_key": api_key,
                    "user_question": question,
                    "generated_qn": question,
                    "sql": sql,
                    "data_csv": data_csv,
                    "sampled": False,
                },
            )
            return analysis.get("summary", "")
        elif os.environ.get("ANALYZE_DATA_MODEL") == "bedrock":
            import boto3

            bedrock = boto3.client(service_name="bedrock-runtime")
            model_id = "meta.llama3-70b-instruct-v1:0"
            accept = "application/json"
            contentType = "application/json"

            body = json.dumps(
                {
                    "prompt": f"""<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Can you please give me the high-level trends (as bullet points that start with a hyphen) of data in a CSV? Note that this CSV was generated to answer the question: `{question}`

This was the SQL query used to generate the table:
{sql}

This was the data generated:
{data_csv}

Do not use too much math in your analysis. Just tell me, at a high level, what the key insights are. Give me the trends as bullet points. No preamble or anything else.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

Here is a summary of the high-level trends in the data:
""",
                    "max_gen_len": 600,
                    "temperature": 0,
                    "top_p": 1,
                }
            )

            response = bedrock.invoke_model(
                body=body, modelId=model_id, accept=accept, contentType=contentType
            )
            model_response = json.loads(response["body"].read())
            print(model_response, flush=True)
            generation = model_response["generation"]
            return generation
