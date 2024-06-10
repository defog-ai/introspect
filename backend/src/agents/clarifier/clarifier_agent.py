# ask an agent what extra information would it need except for the database metadata
# "Clarifier"
import re
import traceback
import yaml
import asyncio
import requests
import os

default_values_formatted = {
    "multi select": [],
    "text input": "",
    # "date range selector": "12 months",
}

# unformatted values
default_values = {
    "multi select": [],
    "text input": "",
    # "date range selector": 12,
}

llm_calls_url = os.environ["LLM_CALLS_URL"]


def parse_q(q):
    try:
        q = re.sub("```", "", q).strip()
        q = re.sub("yaml", "", q).strip()
        j = yaml.safe_load(q.strip())
        for idx in range(len(j)):
            # if this is a multi select, and has no options, change it to a text input
            if (
                j[idx]["ui_tool"] == "multi select"
                and len(j[idx]["ui_tool_options"]) == 0
            ):
                j[idx]["ui_tool"] = "text input"

            j[idx]["response"] = default_values.get(j[idx]["ui_tool"])
            j[idx]["response_formatted"] = default_values_formatted.get(
                j[idx]["ui_tool"]
            )
        return j
    except Exception as e:
        # print(e)
        # traceback.print_exc()
        return []


class Clarifier:
    """
    Ask the user clarifying questions to understand the user's question better.
    """

    def __init__(
        self,
        user_question,
        client_description,
        parent_analyses=[],
        direct_parent_analysis=None,
    ):
        self.user_question = user_question
        self.client_description = client_description
        self.parent_analyses = parent_analyses
        self.direct_parent_analysis = direct_parent_analysis

    @staticmethod
    async def clarifier_post_process(self={}):
        """
        This function is called right before the understander stage.
        It takes in the user's answers to the clarification questions
        and converts them into "user_requirements" which is a string
        that is passed on to the understander.
        """

        async def post_process(res_data):
            print("Running clarifier post process...")
            clarification_questions = res_data["clarification_questions"]

            # gather responses into text
            # pass it to the clarifier as "answers from the user", and ask it to turn them into statements

            url = llm_calls_url
            payload = {
                "request_type": "turn_into_statement",
                "clarification_questions": clarification_questions,
            }
            r = await asyncio.to_thread(requests.post, url, json=payload)
            statements = r.json()["statements"]
            ret = {"assignment_understanding": statements}

            return ret

        return post_process

    async def gen_clarification_questions(self):
        print("Running clarifier...")

        async def generator():
            url = llm_calls_url
            payload = {
                "request_type": "clarify_task",
                "question": self.user_question,
                "client_description": self.client_description,
                "parent_questions": [
                    i["user_question"]
                    for i in self.parent_analyses
                    if i["user_question"] is not None and i["user_question"] != ""
                ],
                "direct_parent_analysis": self.direct_parent_analysis,
            }
            r = await asyncio.to_thread(requests.post, url, json=payload)
            res = r.json()
            clarifying_questions = res["clarifications"]
            try:
                cleaned_clarifying_questions = parse_q(clarifying_questions)
                print(cleaned_clarifying_questions)
                for q in cleaned_clarifying_questions:
                    try:
                        if q is not None:
                            yield [q]
                    except Exception as e:
                        print(e)
                        pass
            except Exception as e:
                traceback.print_exc()
                print(e)
                yield None

        return generator, await self.clarifier_post_process()
