import traceback

import yaml
from agents.clarifier.clarifier_agent import Clarifier
from utils import get_clean_plan
from db_utils import (
    get_multiple_reports,
    get_report_data,
    update_report_data,
)
from agents.main_agent import (
    execute,
    get_clarification,
)

request_types = [
    "clarify",
    "gen_steps",
]

prop_names = {
    "clarify": "clarification_questions",
    "gen_steps": "steps",
}

import os

dfg_api_key = os.environ["DEFOG_API_KEY"]


class ReportDataManager:
    def __init__(self, user_question, report_id):
        self.report_id = report_id
        self.report_data = None
        self.api_key = dfg_api_key
        self.user_question = user_question
        self.invalid = False
        self.similar_plans = []
        self.was_async_init_called = False
        # check if this report exists in the main db
        # if so, load the report details from there
        err1, report_data = get_report_data(report_id)

        # if there are parent_analyses, get the user_question from each of them
        err2, parent_analyses = get_multiple_reports(
            report_data.get("parent_analyses") or []
        )
        self.parent_analyses = parent_analyses

        self.direct_parent_id = report_data.get("direct_parent_id")
        self.direct_parent_analysis = None

        err3 = None

        if self.direct_parent_id:
            err3, self.direct_parent_analysis = get_report_data(self.direct_parent_id)
            # if we get something valid, we only need two things:
            # the user question, and the generated steps in yaml format
            if err3 is None:
                # if this has gen_steps
                # and if we had actual steps in the gen_steps
                if (
                    self.direct_parent_analysis.get("gen_steps", None)
                    and len(self.direct_parent_analysis["gen_steps"]["steps"]) > 0
                ):
                    clean_plan = get_clean_plan(self.direct_parent_analysis)

                    self.direct_parent_analysis = {
                        "user_question": self.direct_parent_analysis.get(
                            "user_question"
                        ),
                        "plan": clean_plan,
                        "plan_yaml": yaml.dump(clean_plan),
                    }

        self.invalid = err1 or err2 or err3

        if self.invalid is None and report_data is not None:
            self.report_data = report_data
            self.report_id = report_data.get("report_id")

            self.agents = {
                "clarify": get_clarification,
                "gen_steps": execute,
            }

            self.post_processes = {
                "clarify": Clarifier.clarifier_post_process,
            }

    # have to call this separately because update_report_data is an async function
    # sorry :/
    async def async_init(self):
        self.was_async_init_called = True
        if not self.invalid:
            # update with latest user question
            # we also update the embedding in this function
            err = await update_report_data(
                self.report_id, "user_question", self.user_question, True
            )

            if err is not None:
                print(err)

            similar_plans = []

            # only get model_generate_inputs, description, done and outputs_storage_keys from the plans
            for i, p in enumerate(similar_plans):
                filtered_p = {}
                filtered_p["user_question"] = p.get("user_question", "")
                filtered_p["plan"] = p.get("plan", [])
                for j, s in enumerate(filtered_p["plan"]):
                    filtered_p["plan"][j] = {
                        "description": s.get("description", ""),
                        "tool_name": s.get("tool_name", ""),
                        "inputs": s.get("model_generated_inputs", {}),
                        "outputs_storage_keys": s.get("outputs_storage_keys", []),
                        "done": s.get("done", False),
                    }

                similar_plans[i] = filtered_p

            self.similar_plans = similar_plans

    async def update(
        self, request_type=None, new_data=None, replace=False, overwrite_key=None
    ):
        if (
            request_type is None
            or new_data is None
            or request_type not in request_types
        ):
            return

        err = await update_report_data(
            self.report_id, request_type, new_data, replace, overwrite_key
        )
        if err is not None:
            print(err)
            return
        # update the report data in memory
        self.report_data[request_type] = new_data

    async def run_agent(self, request_type=None, post_process_data={}, **kwargs):
        err = None
        result = None

        if not self.was_async_init_called:
            await self.async_init()

        try:
            if request_type is None or request_type not in self.agents:
                raise ValueError("Incorrect request type")

            # remove existing data for this request_type
            # and all the request types after this one
            idx = request_types.index(request_type)
            print("Cleaning existing data")
            for i in range(idx, len(request_types)):
                err = await self.update(request_types[i], [], True)

            # find the last request type in the request_types array if this is not "clarify"
            # for post processing
            last_request_type = "noop"
            if request_type != "clarify":
                last_request_type = request_types[request_types.index(request_type) - 1]
                # update the report data manager with the latest data with user inputs from the last stage
                err = await self.update(
                    last_request_type,
                    post_process_data[prop_names[last_request_type]],
                    replace=True,
                )

            if last_request_type in ["noop", "gen_report"]:
                post_processing_arguments = {}
            elif last_request_type in ["understand", "gen_steps"]:
                # these are not doing any async stuff
                # so we can just call them directly
                post_processing_function = self.post_processes[last_request_type]()
                post_processing_arguments = post_processing_function(post_process_data)
            else:
                post_processing_function = await self.post_processes[
                    last_request_type
                ]()
                post_processing_arguments = await post_processing_function(
                    post_process_data
                )

            result, post_process = await self.agents[request_type](
                **kwargs,
                **post_processing_arguments,
                parent_analyses=self.parent_analyses,
                similar_plans=self.similar_plans,
                direct_parent_analysis=self.direct_parent_analysis,
            )

            if result["success"] is not True:
                raise ValueError(
                    result.get("error_message") or "Error generating report"
                )

            self.post_processes[request_type] = post_process
            # print(generator_func)

        except Exception as e:
            err = str(e)
            print(e)
            result = None
            traceback.print_exc()
        finally:
            return err, result
