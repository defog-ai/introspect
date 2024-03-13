# the executor converts the user's task to steps and maps those steps to tools.
# also runs those steps
from uuid import uuid4

from agents.planner_executor.execute_tool import execute_tool
from agents.planner_executor.tool_helpers.core_functions import resolve_input
from db_utils import store_tool_run
from utils import warn_str, YieldList
from .tool_helpers.toolbox_manager import get_tool_library
from .tool_helpers.tool_param_types import ListWithDefault
import asyncio
import requests

import yaml
import re
import pandas as pd


with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

dfg_api_key = env["api_key"]


class Executor:
    """
    Convert task into steps
    where each step is mapped to a tool.
    """

    def __init__(
        self,
        report_id,
        user_question,
        client_description,
        glossary,
        table_metadata_csv,
        assignment_understanding,
        dfg,
        dfg_api_key="",
        toolboxes=[],
        parent_analyses=[],
    ):
        self.user_question = user_question
        self.client_description = client_description
        self.glossary = glossary
        self.table_metadata_csv = table_metadata_csv
        self.dfg_api_key = dfg_api_key
        self.toolboxes = toolboxes
        self.assignment_understanding = assignment_understanding
        self.analysis_id = report_id
        self.parent_analyses = parent_analyses
        self.previous_responses = []

        self.dfg = dfg
        self.tool_library = get_tool_library(toolboxes)

        self.global_dict = {
            "user_question": user_question,
            "client_description": client_description,
            "glossary": glossary,
            "table_metadata_csv": table_metadata_csv,
            "dfg_api_key": dfg_api_key,
            "toolboxes": toolboxes,
            "assignment_understanding": assignment_understanding,
            "dfg": None,
        }

        # keep storing store column names of each step's generated data
        self.tool_outputs_column_descriptions = ""

    @staticmethod
    def planner_executor_post_process(self={}):
        def post_process(x):
            return {}

        return post_process

    async def execute(self):
        async def generator():
            max_retries = 2
            retries = 0
            steps = []
            """SAMPLE:

            description: "Fetch the required data from the database"
            done: false
            inputs: ['Get patient_id, celltype, treatment, survival_in_days, and status from the patients table']
            outputs_storage_keys: ['patient_data']
            tool_name: "data_fetcher_and_aggregator"
            tool_run_id: "3496f202-92d3-4c06-a6b2-a093f9867a00"

            description: "Generate a Kaplan Meier survival curve stratified by cell type and treatment type"
            done: true
            inputs: (4) ['global_dict.patient_data', 'survival_in_days', 'status', Array(2)]
            outputs_storage_keys: ['km_curve_data']
            tool_name: "kaplan_meier_curve"
            tool_run_id: "a46c91e7-6ea7-4b0e-b3de-c684803a7b47"

            """
            next_step_data_description = ""
            while True:
                url = "https://defog-llm-calls-ktcmdcmg4q-uc.a.run.app"

                if next_step_data_description.startswith("There was an error"):
                    payload = {
                        "request_type": "fix_error",
                        "question": self.user_question,
                        "metadata": self.table_metadata_csv,
                        "toolbox": self.tool_library,
                        "assignment_understanding": self.assignment_understanding,
                        "parent_questions": [
                            p["user_question"] for p in self.parent_analyses
                        ],
                        "previous_responses": self.previous_responses,
                        "next_step_data_description": "",
                        "error": next_step_data_description,
                        "erroreous_response": ans,
                    }
                    ans = await asyncio.to_thread(requests.post, url, json=payload)
                else:
                    payload = {
                        "request_type": "create_plan",
                        "question": self.user_question,
                        "metadata": self.table_metadata_csv,
                        "toolbox": self.tool_library,
                        "assignment_understanding": self.assignment_understanding,
                        "parent_questions": [
                            p["user_question"] for p in self.parent_analyses
                        ],
                        "previous_responses": self.previous_responses,
                        "next_step_data_description": next_step_data_description,
                    }
                    ans = await asyncio.to_thread(requests.post, url, json=payload)
                ans = ans.json()["generated_step"]
                print(ans)

                match = re.search("(?:```yaml)([\s\S]*?)(?=```)", ans)

                if match is None:
                    break

                step = yaml.safe_load(match[1].strip())[0]

                # add a unique id to this tool as the tool_run prop
                step["tool_run_id"] = str(uuid4())

                print(step)

                # prepare to execute this step, by resolving the inputs
                # if there's a global_dict.variable_name reference in step["inputs"], replace it with the value from global_dict
                resolved_inputs = resolve_input(step["inputs"], self.global_dict)

                # execute this step
                result, tool_function_parameters = await execute_tool(
                    step["tool_name"], resolved_inputs, self.global_dict
                )

                step["error_message"] = result.get("error_message")

                self.previous_responses.append(ans)

                step["function_signature"] = tool_function_parameters
                # when we're re running, we will need to reconstruct the model messages
                # store these for later
                # later we'll have to replace these with the user's edited inputs perhaps.
                step["model_generated_inputs"] = step["inputs"].copy()

                # use function signature to fill in all the remaining inputs
                # both are arrays, so fill in the remaining inputs with default values from function parameters
                if len(step["function_signature"]) > len(step["inputs"]):
                    for i in range(
                        len(step["inputs"]), len(step["function_signature"])
                    ):
                        default = step["function_signature"][i].get("default")
                        if isinstance(default, ListWithDefault):
                            # get the default value of this list
                            step["inputs"].append(default.default_value)

                        # if this is a normal list, then just use the first value
                        elif isinstance(default, list):
                            step["inputs"].append(default[0])
                        else:
                            step["inputs"].append(default)

                # if there's no error, check if zip is possible
                # this should never really happen
                if not result.get("error_message") and (
                    len(step.get("outputs_storage_keys")) != len(result.get("outputs"))
                ):
                    # TODO: REDO THIS STEP
                    print("Length of outputs_storage_keys and outputs don't match")
                    pass

                # if we're here, means this step ran successfully.
                # if the outputs of this step match any of the previous steps, either exactly or:
                # , means that we should overwrite the previous step with this step. this was probably a "correction" of some of the previous step.
                is_correction = False

                yield_val = YieldList([step])

                for i, previous_step in enumerate(steps):
                    if set(previous_step["outputs_storage_keys"]) == set(
                        step["outputs_storage_keys"]
                    ):
                        print("\n")
                        print("This step is a correction of a previous step")
                        print("\n\n")
                        is_correction = True
                        # we've already written that step, and sent it to the front end.
                        # steal the tool_run_id of the older step
                        step["tool_run_id"] = previous_step["tool_run_id"]
                        step["tool_run_data"] = {}
                        yield_val.overwrite_key = "tool_run_id"

                if not is_correction:
                    steps.append(step)

                # store tool run
                store_result = await store_tool_run(self.analysis_id, step, result)

                if store_result["success"] is False:
                    print("Tool run storage failed")
                    print(store_result.get("error_message"))
                    break

                # retry logic if there's an error message
                if result.get("error_message"):
                    retries += 1
                    if retries >= max_retries:
                        print(
                            f"Error running tool {step['tool_name']} after {max_retries} retries"
                        )
                        print("Error message: ", result["error_message"])
                        yield yield_val
                        break

                    print(
                        "There was an error running the tool: ",
                        result["error_message"],
                    )
                    print("Retrying...")
                    next_step_data_description = f"There was an error running the tool {step['tool_name']}. This was the error:\n{result['error_message']}\n Instead of suffixing older output names with _updated, _v2, etc, re use the older output names of previously generated steps."
                    continue

                yield yield_val

                for key, output in zip(step["outputs_storage_keys"], result["outputs"]):
                    data = output.get("data")
                    # if output data exists and data type is a pandas dataframe
                    # store the column names in the tool_outputs_column_descriptions
                    if data is not None and type(data) == type(pd.DataFrame()):
                        # if there's an overwrite key, check if there's a line that already exists
                        replace_line = re.search(
                            f"({key}: pd.DataFrame with )([\s\S]*?)(?=\\n)",
                            self.tool_outputs_column_descriptions,
                        )
                        if yield_val.overwrite_key and replace_line:
                            self.tool_outputs_column_descriptions = self.tool_outputs_column_descriptions.replace(
                                replace_line.group(2),
                                f"{len(data)} rows and columns: {list(data.columns)[:20]}",
                            )
                        else:
                            # store max 20 columns
                            self.tool_outputs_column_descriptions += f"\n{key}: pd.DataFrame with {len(data)} rows and columns: {list(data.columns)[:20]}\n"

                        self.global_dict[key] = data
                        # name the df too
                        self.global_dict[key].name = key
                        # warn if more than 20 columns
                        warn_str(
                            f"More than 20 columns in dataset generated for {key}. Only storing the first 20."
                        )

                if self.tool_outputs_column_descriptions:
                    # if there's an overwrite key, replace the
                    next_step_data_description = f"The global_dict contains the following keys with data and columns:\n```{self.tool_outputs_column_descriptions}```\n"

                print(next_step_data_description)

                # if we still have an error in result, we somehow beat the max_retries check in the if condition above
                # so we should break out of the loop
                # this should never happen in normal circumstances
                if "error_message" in result:
                    print(result["error_message"])
                    break

                if "done" in step and step["done"] is True:
                    break

        return generator, self.planner_executor_post_process()
