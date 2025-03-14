from agents import Agent, RunContextWrapper
from pydantic import BaseModel
from tools.analysis_models import EvaluatorAgentOutput, GenerateReportOpenAIAgentsOutput


class UserContext(BaseModel):
    question: str
    db_name: str
    metadata_str: str
    clarification_responses: str
    pdf_file_ids: list[str]


def analyst_instructions(
    wrapper: RunContextWrapper[UserContext], agent: Agent[UserContext]
) -> str:
    if len(wrapper.context.pdf_file_ids) > 0:
        pdf_instruction = f"with IDs {wrapper.context.pdf_file_ids}"
    else:
        pdf_instruction = ""

    return f"""Analyze data to answer {wrapper.context.question} using all available tools: the database ({wrapper.context.db_name}), the internet, or provided PDFs {pdf_instruction}. Always explore multiple angles, dig deep and extract details by asking multiple questions.
    
    - If follow-up questions or feedback are provided, take them into consideration when generating your questions for the database, web search, or PDFs.
    - Always interpret the question to be in context of the database schema.
    - Always use the database first. When using the text_to_sql tool, ask only questions that can be answered based on its schema. 
    - Only use the web search tool if the question requires real-time information, cannot be answered by the database, or additional information is needed to support the analysis.
    - When using the web search tool, vary keywords and sources to expand the search.
    - Do not ask the exact same question twice. Always ask new questions or rephrase the previous question if it led to an error. 

The database schema is below:
```sql
{wrapper.context.metadata_str}
"""


analysis_agent = Agent[UserContext](
    name="data analyst",
    instructions=analyst_instructions,
    tools=[],  # Will be set dynamically
)


evaluator_agent = Agent[UserContext](
    name="evaluator",
    instructions="""Your task is to evaluate all current analyses and their results and determine if the research is comprehensive enough or if more follow-up questions are needed. Always consider the user's question from multiple perspectives and assess if the current research addresses all important aspects of the original question.

If you believe more research is needed:
1. List 1-3 specific follow-up questions that would address important gaps in the current research but remain in context of the original question, database schema and provided PDFs. IMPORTANT: The questions MUST be phrased in a way that can be answered by the database, the internet, or provided PDFs.
2. Briefly explain why the existing research is insufficient to answer the original question.

If you believe the research is already comprehensive:
1. State that no further research is needed
2. Briefly explain why the existing research adequately answers the original question or why the original question is not answerable with the available tools.
""",
    output_type=EvaluatorAgentOutput,
)


def report_instructions(
    wrapper: RunContextWrapper[UserContext], agent: Agent[UserContext]
) -> str:
    return f"""Based on all given analyses and information gathered, you are to write a detailed descriptive report that answers the very first original question: {wrapper.context.question}. Cite specific numbers, tables, and information sources from the analyses to back your statements. Try to break down your answer into clear and understandable categories in the report. If you include responses from the web search tool, please cite your sources inline and provide a link to them."""


report_agent = Agent[UserContext](
    name="report generator",
    instructions=report_instructions,
    model="gpt-4o",
    tools=[],
)
