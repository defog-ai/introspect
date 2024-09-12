# the executor converts the user's task to steps and maps those steps to tools.
# also runs those steps
from uuid import uuid4


from agents.planner_executor.execute_tool import execute_tool
from agents.planner_executor.tool_helpers.core_functions import resolve_input
from .tool_helpers.toolbox_manager import get_tool_library_prompt
from generic_utils import make_request
from copy import deepcopy

import yaml
import re
import pandas as pd
import os


llm_calls_url = os.environ.get("LLM_CALLS_URL", "https://api.defog.ai/agent_endpoint")
analysis_assets_dir = os.environ.get(
    "ANALYSIS_ASSETS_DIR", "/agent-assets/analysis-assets"
)


class RESTExecutor:
    """
    Convert task into steps, where each step is mapped to a tool.
    Currently does not support error correction.
    TODO: To simplify our code, we should probably refactor error correction into a separate function (with retries)
    """

    def __init__(
        self,
        dfg_api_key,
        user_question,
        assignment_understanding,
        toolboxes=[],
        dev=False,
    ):
        self.user_question = user_question
        self.dfg_api_key = dfg_api_key
        self.toolboxes = toolboxes
        self.assignment_understanding = assignment_understanding
        self.previous_responses = []
        self.dev = dev

        self.global_dict = {
            "user_question": user_question,
            "dfg_api_key": dfg_api_key,
            "toolboxes": toolboxes,
            "assignment_understanding": assignment_understanding,
            "dfg": None,
            "llm_calls_url": llm_calls_url,
            "analysis_assets_dir": analysis_assets_dir,
            "dev": dev,
        }

        # keep storing store column names of each step's generated data
        self.tool_outputs_column_descriptions = ""

    async def execute(self):
        self.tool_library_prompt = await get_tool_library_prompt(
            self.toolboxes, self.user_question
        )

        is_done = False
        steps = []
        success = True

        while not is_done:
            next_step_data_description = ""

            # make calls to the LLM to get the next step
            llm_server_url = os.environ.get("LLM_SERVER_ENDPOINT", None)
            if not llm_server_url:
                llm_server_url = None
                print("LLM_SERVER_ENDPOINT not set, using None", flush=True)
            else:
                print(f"LLM_SERVER_ENDPOINT set to {llm_server_url}", flush=True)
            payload = {
                "request_type": "create_plan",
                "question": self.user_question,
                "tool_library_prompt": self.tool_library_prompt,
                "assignment_understanding": self.assignment_understanding,
                "previous_responses": self.previous_responses,
                "next_step_data_description": next_step_data_description,
                "api_key": self.dfg_api_key,
                "plan_id": str(uuid4()),
                "similar_plans": [],
                "parent_questions": [],
                "llm_server_url": os.environ.get("LLM_SERVER_ENDPOINT", None),
                "model_name": os.environ.get("LLM_MODEL_NAME", None),
            }
            ans = await make_request(llm_calls_url, data=payload)

            ans = ans["generated_step"]
            self.previous_responses.append(ans)

            match = re.search("(?:```yaml)([\s\S]*?)(?=```)", ans)
            step = yaml.safe_load(match[1].strip())[0]
            step["tool_run_id"] = str(uuid4())

            # resolve the inputs of the step to actual values that can be used in the tool
            # this helps in resolving global_dict.variable_name references, as well as handling errors
            resolved_inputs = {}

            for input_name, val in step["inputs"].items():
                resolved_inputs[input_name] = resolve_input(val, self.global_dict)

                # prepare to execute this step, by resolving the inputs
                # if there's a global_dict.variable_name reference in step["inputs"], replace it with the value from global_dict
                resolved_inputs = {}
                for input_name, val in step["inputs"].items():
                    resolved_inputs[input_name] = resolve_input(val, self.global_dict)

            # execute this step
            result, tool_input_metadata = await execute_tool(
                step["tool_name"], resolved_inputs, self.global_dict
            )

            step["error_message"] = result.get("error_message")
            if not step["error_message"]:
                step["input_metadata"] = tool_input_metadata
                step["result"] = deepcopy(result)
                for idx, item in enumerate(step["result"]["outputs"]):
                    if "data" in item:
                        if isinstance(item["data"], pd.DataFrame):
                            step["result"]["outputs"][idx]["data"] = item[
                                "data"
                            ].to_csv(index=False)

                for key, output in zip(step["outputs_storage_keys"], result["outputs"]):
                    data = output.get("data")
                    # if output data exists and data type is a pandas dataframe
                    # store the column names in the tool_outputs_column_descriptions
                    if data is not None and isinstance(data, pd.DataFrame):
                        # if there's an overwrite key, check if there's a line that already exists
                        self.tool_outputs_column_descriptions += f"\n{key}: pd.DataFrame with {len(data)} rows and columns: {list(data.columns)[:20]}\n"

                        self.global_dict[key] = data
                        # name the df too
                        self.global_dict[key].df_name = key

                is_done = step.get("done")
            else:
                # if there's an error, we should stop executing the steps
                # and return the error message
                success = False
                is_done = True

            steps.append(step)

            if self.tool_outputs_column_descriptions:
                next_step_data_description = f"The global_dict contains the following keys with data and columns:\n```{self.tool_outputs_column_descriptions}```\n"
        return steps, success
