import sys
from agents.clarifier.clarifier_agent import Clarifier
from agents.planner_executor.planner_executor_agent import Executor
import traceback
import yaml

# from db_utils import add_report_markdown

with open(".env.yaml", "r") as f:
    env = yaml.safe_load(f)

dfg_api_key = env["api_key"]


# each of the agents can return a "postprocess" function
# that will be run before the next stage and will process the incoming user input if any for the next stage
async def get_clarification(
    user_question="",
    client_description="",
    table_metadata_csv="",
    glossary="",
    parent_analyses=[],
    **kwargs,
):
    """
    This function is called when the user asks for clarification questions.
    It creates a clarifier object and calls the gen_clarification_questions function
    on it. This function returns a generator that yields clarification questions.
    """
    try:
        clarifier = Clarifier(
            user_question,
            client_description,
            glossary,
            table_metadata_csv,
            parent_analyses,
        )

        (
            clarification_questions,
            post_process,
        ) = await clarifier.gen_clarification_questions()

        return {
            "success": True,
            "generator": clarification_questions,
            "prop_name": "clarification_questions",
        }, post_process
    except Exception as e:
        err = e
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Error generating clarification questions.",
        }, None


async def execute(
    report_id="",
    user_question="",
    client_description="",
    table_metadata_csv="",
    assignment_understanding="",
    glossary="",
    db_creds=None,
    toolboxes=[],
    parent_analyses=[],
    **kwargs,
):
    """
    This function is called after the user submits the approaches.
    It creates an executor object and calls the execute function on it.
    This function returns a generator that yields the report sections, intro and conclusion.
    This takes quite long as of now. Needs to be parallelised for the future.
    """
    print("Evaling approaches")
    
    executor = Executor(
        report_id,
        user_question,
        client_description,
        glossary,
        table_metadata_csv,
        assignment_understanding,
        None,
        dfg_api_key=dfg_api_key,
        toolboxes=toolboxes,
        parent_analyses=parent_analyses,
    )
    try:
        execute, post_process = await executor.execute()
        return {
            "success": True,
            "generator": execute,
            "prop_name": "steps",
        }, post_process

    except Exception as e:
        err = e
        traceback.print_exc()
        return {"success": False, "error_message": "Error generating report."}, None
