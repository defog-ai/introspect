"""
Model name definitions that we use from various LLM providers
"""
from typing import List
import openai
import anthropic

# OpenAI Models
O3_MINI = "o3-mini"
O1 = "o1"
O1_MINI = "o1-mini"
GPT_4O = "gpt-4o"
GPT_4O_MINI = "gpt-4o-mini"
GPT_4_TURBO = "gpt-4-turbo"

# Anthropic Models
CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"

ALL_MODELS = [O3_MINI, O1_MINI, GPT_4O, GPT_4O_MINI, CLAUDE_3_5_SONNET]

# we can get the list of models supported by the OpenAI SDK by converting the 
# openai.types.ChatModel type to a list as it is a Literal type (list of strings)
# we can't do the same for Anthropic as the Model type is a Union type wrapping
# a string and a Literal type (list of strings)
OPENAI_SDK_MODELS = list(openai.types.ChatModel.__args__)

def validate_models(models: List[str]):
    """
    Validate that all models are available in the current version of their
    respective LLM API libraries. This is to avoid runtime errors when we
    upgrade the model specified in our codebase, but have yet to rebuild
    our docker image to pull in the latest version of the LLM API library.
    """
    for model in models:
        if model.startswith(("o", "gpt")):
            if model not in OPENAI_SDK_MODELS:
                raise ValueError(f"Invalid OpenAI model: {model}")
            else:
                print(f"{model} is supported by OpenAI version {openai.__version__}")
        elif model.startswith("claude"):
            if not isinstance(model, anthropic.types.model.Model):
                raise ValueError(f"Invalid Anthropic model: {model}")
            else:
                print(f"{model} is supported by Anthropic version {anthropic.__version__}")
        else:
            raise ValueError(f"Unknown model provider for model: {model}")
