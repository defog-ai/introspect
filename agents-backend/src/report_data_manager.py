import traceback
from agents.clarifier.clarifier_agent import Clarifier
from db_utils import get_parent_analyses, get_report_data, update_report_data
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


class ReportDataManager:
    def __init__(self, user_question, report_id, db_creds=None):
        self.report_id = report_id
        self.report_data = None
        self.user_question = user_question
        self.invalid = False
        # check if this report exists in the main db
        # if so, load the report details from there
        err1, report_data = get_report_data(report_id)

        self.db_creds = db_creds

        # if there are parent_analyses, get the user_question from each of them
        err2, parent_analyses = get_parent_analyses(
            report_data.get("parent_analyses") or []
        )
        self.parent_analyses = parent_analyses

        self.invalid = err1 or err2

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

            if not self.invalid:
                # update with latest user question
                update_report_data(
                    self.report_id, "user_question", self.user_question, True
                )

    def update(
        self, request_type=None, new_data=None, replace=False, overwrite_key=None
    ):
        if (
            request_type is None
            or new_data is None
            or request_type not in request_types
        ):
            return

        err = update_report_data(
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

        try:
            if request_type is None or request_type not in self.agents:
                raise ValueError("Incorrect request type")

            # remove existing data for this request_type
            # and all the request types after this one
            idx = request_types.index(request_type)
            print("Cleaning existing data")
            for i in range(idx, len(request_types)):
                err = self.update(request_types[i], [], True)

            # find the last request type in the request_types array if this is not "clarify"
            # for post processing
            last_request_type = "noop"
            if request_type != "clarify":
                last_request_type = request_types[request_types.index(request_type) - 1]
                # update the report data manager with the latest data with user inputs from the last stage
                self.update(
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
                parent_analyses=self.parent_analyses
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
