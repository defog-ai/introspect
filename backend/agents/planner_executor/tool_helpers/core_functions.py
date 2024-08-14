import base64
import os
from typing import Dict, List

import pandas as pd
import tiktoken

from utils_llm import llm_call

report_assets_dir = os.environ.get("REPORT_ASSETS_DIR", "./report_assets")


def encode_image(image_path):
    """
    Encodes an image to base64.
    """
    image_path = os.path.join(report_assets_dir, image_path)
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


def estimate_tokens_left(messages: List[Dict], model: str) -> int:
    """
    Returns an estimate of the number of tokens left for generation based on the
    messages generated so far and the model used.
    """
    encoding = tiktoken.encoding_for_model(model)
    total_tokens = 0
    for msg in messages:
        num_tokens = len(encoding.encode(msg["content"]))
        total_tokens += num_tokens
    if model == "gpt-3.5-turbo":
        return 4000 - total_tokens
    elif "gpt-4" in model:
        return 8000 - total_tokens
    else:
        raise ValueError(f"Unsupported model {model}")


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


async def analyse_data(
    question: str, data: pd.DataFrame, image_path: str = None
) -> str:
    """
    Generate a short summary of the results for the given qn.
    """
    if data is None:
        yield {"success": False, "model_analysis": "No data found"}
        return

    if data.size > 50 and image_path is None:
        yield {"success": False, "model_analysis": "NONE"}
        return

    if question is None or question == "":
        yield {"success": False, "model_analysis": "No question provided"}
        return

    if image_path:
        base64_image = encode_image(image_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"An image was generated to answer this question: `{question}`. Please interpret the results of this image for me. Do not repeat the data in the image verbatim. Instead, focus on the key insights and takeaways. Assume that your audience is a non-technical stakeholder who is interested in high level insights but do not want the exact numbers in the image to be repeated.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "low",
                        },
                    },
                ],
            },
        ]
    else:
        df_csv = data.to_csv(float_format="%.3f", header=True)
        user_analysis_prompt = f"""Generate a short summary of the results for the given qn: `{question}`\n\nand results:
    {df_csv}\n\n```"""
        analysis_prompt = f"""Here is the brief summary of how the results answer the given qn:\n\n```"""
        # get comma separated list of col names
        col_names = ",".join(data.columns)

        messages = [
            {
                "role": "assistant",
                "content": f"User has the following columns available to them:\n\n"
                + col_names
                + "\n\n",
            },
            {"role": "user", "content": user_analysis_prompt},
            {
                "role": "assistant",
                "content": analysis_prompt,
            },
        ]

    completion = await llm_call(
        model="gpt-4o",
        messages=messages,
        temperature=0,
        seed=42,
        max_tokens=400,
    )

    async for chunk in completion:
        ct = chunk.choices[0]

        if ct.finish_reason == "stop":
            return

        yield {"success": True, "model_analysis": ct.delta.content}
