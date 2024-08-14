import os

from generic_utils import make_request

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")

async def llm_call(model, messages, **kwargs):
    result = await make_request(DEFOG_BASE_URL + "/llm_call", {
        "model": model,
        "messages": messages,
        **kwargs
    })
    return result