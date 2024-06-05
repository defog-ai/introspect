from datetime import datetime
import functions_framework
from openai import OpenAI
import os
import pandas as pd
import json
from io import StringIO
import yaml
from prompts import (
    basic_plan_system_prompt,
    basic_user_prompt,
    tweak_parent_analysis_system_prompt,
    tweak_parent_analysis_user_prompt,
    generate_tool_code_system_prompt,
    generate_tool_code_user_prompt,
)

openai_api_key = os.environ["OPENAI_API_KEY"]

openai = OpenAI(api_key=openai_api_key)

model = "gpt-4o"


def clean_response(res):
    if type(res) is tuple or type(res) is list and len(res) != 0:
        return ", ".join(res)
    elif type(res) is str and res != "":
        return res
    else:
        return "Not answered. Assume default value"


# with open("./cell_dict.json", "r") as f:
#     cell_dict = json.load(f)


async def analyse_data(question: str, data: pd.DataFrame) -> str:
    """
    Generate a short summary of the results for the given qn.
    """
    df_csv = data.to_csv(float_format="%.3f", header=True)
    user_analysis_prompt = f"""Generate a short summary of the results for the given qn: `{question}`\n\nand results:
{df_csv}\n\n```"""
    analysis_prompt = (
        f"""Here is the brief summary of how the results answer the given qn:\n\n```"""
    )
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

    completion = openai.chat.completions.create(
        model=model, messages=messages, temperature=0, seed=42
    )
    model_analysis = completion.choices[0].message.content
    return {"model_analysis": model_analysis}


def create_plan(
    user_question,
    similar_plans,
    table_metadata_csv,
    assignment_understanding,
    parent_questions,
    previous_responses,
    next_step_data_description,
    tool_library_prompt,
    error=None,
    erroreous_response=None,
    direct_parent_analysis=None,
):
    parent_analyses_prompt = (
        ""
        if len(parent_questions) == 0
        else f"\nThis task is a follow up to the following previous tasks:\n"
        + "\n".join([f"""- {p}""" for p in parent_questions])
    )

    print(user_question)
    print(assignment_understanding)

    assignment_understanding_prompt = (
        ""
        if assignment_understanding == ""
        else f"""Make sure you follow the following guidelines when formulating your steps:
{assignment_understanding}"""
    )

    system_prompt = None
    user_prompt = None

    if not direct_parent_analysis:
        system_prompt = basic_plan_system_prompt.format(
            tool_library_prompt=tool_library_prompt,
            table_metadata_csv=table_metadata_csv,
        )
        user_prompt = basic_user_prompt.format(
            user_question=user_question,
            parent_analyses_prompt=parent_analyses_prompt,
            assignment_understanding_prompt=assignment_understanding_prompt,
        )
    else:
        system_prompt = tweak_parent_analysis_system_prompt.format(
            tool_library_prompt=tool_library_prompt,
            table_metadata_csv=table_metadata_csv,
            original_user_question=direct_parent_analysis["user_question"],
            original_plan=direct_parent_analysis["plan_yaml"],
        )
        user_prompt = tweak_parent_analysis_user_prompt.format(
            user_question=user_question,
            parent_analyses_prompt=parent_analyses_prompt,
            assignment_understanding_prompt=assignment_understanding_prompt,
        )

    print(system_prompt)
    print(user_prompt)

    if len(similar_plans) > 0:
        similar_plans_yaml = yaml.dump(
            similar_plans, sort_keys=False, default_flow_style=False
        )
        user_prompt += f"""\n\nIf relevant to the question asked, you can use the following FULL plans as references for answering the question:"""
        user_prompt += (
            f"""\n\n```yaml\n"""
            + similar_plans_yaml
            + f"""\n```"""
            + "\n\nNote that those are full plans with all the steps. You still only need to generate one step at a time."
        )

    user_prompt = user_prompt.strip()

    print(user_prompt)

    subsequent_prompts = []
    for idx, item in enumerate(previous_responses):
        subsequent_prompts.append(
            {
                "role": "assistant",
                "content": item,
            }
        )

        if idx == len(previous_responses) - 1:
            subsequent_prompts.append(
                {
                    "role": "user",
                    "content": f"{next_step_data_description}Give the task and your previous responses, what is your next step?",
                }
            )
        else:
            subsequent_prompts.append(
                {
                    "role": "user",
                    "content": f"Give the task and your previous responses, what is your next step?",
                }
            )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ] + subsequent_prompts
    if error is not None:
        messages += [
            {
                "role": "user",
                "content": error
                + "\n\nPlease generate a new step with fixes. Don't regenerate previous steps.",
            }
        ]
    completion = openai.chat.completions.create(
        model=model, messages=messages, temperature=0, seed=42
    )
    generated_step = completion.choices[0].message.content.strip()

    return {"generated_step": generated_step}


def get_clarification(
    user_question,
    client_description,
    table_metadata_csv,
    parent_questions=None,
    direct_parent_analysis=None,
):
    system_prompt = f"""You are a data analyst who has been asked a question about a dataset.

Your job is to determine if a question is clear, and ask clarifying questions (if any) to the client.
{client_description}

If the user's question does not involve one of these scenarios, just respond with "No clarification is needed"
"""

    user_prompt = f"""Here is the user's question: {user_question}

Do you have any clarifications you need from the user? You are only allowed to ask a single clarification. Return just the clarifying question as a short sentence, nothing else."""

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
    completion = openai.chat.completions.create(
        model=model, messages=messages, temperature=0, seed=42, max_tokens=64
    )
    clarifications = completion.choices[0].message.content
    if "no clarification" not in clarifications.lower():
        clarifications = f"""```yaml
- question: "{clarifications}"
  ui_tool: text input
```"""
    return {"clarifications": clarifications}


def turn_into_statement(clarification_questions):
    if not clarification_questions or len(clarification_questions) == 0:
        print("Generating a blank statement")
        return {"statements": ""}

    qna = "\n".join(
        [
            f'Q. {q["question"]}\nAns. {clean_response(q["response"])}'
            for q in clarification_questions
        ]
    )
    # print(qna)
    system_prompt = "Your role is to convert Question/Answer format messages into statements in a numbered list. Only return statements as a numbered list, nothing else."
    user_prompt = f"Here are the responses:\n\n{qna}\n\nConvert these into numbered statements. Only give me these statements, nothing else."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    completion = openai.chat.completions.create(
        model=model, messages=messages, temperature=0, seed=42
    )
    statements = completion.choices[0].message.content
    print(statements)
    return {"statements": statements}


def generate_sql(question, metadata, glossary):
    # identify if this question contains a cytokine, a gene or a general cell type, or neither
    question = question.replace("GEN", "GCT")

    messages = [
        {
            "role": "system",
            "content": """Your role is to determine if a given statement mentions a cytokine, a gene or cell-type, both, or something else.
Typically, cytokines are written as IL-6, IL-10 etc.
Typically, genes or cell types are written as CD4+, memory T cells, KI67+, CD45RA+ etc.

Give your answer as just a single string. Your answer must be one of the following: ['gene_or_cell', 'cytokine', 'both', 'other']
""",
        },
        {
            "role": "user",
            "content": f"Does this staetment mention a cytokine, a gene_or_cell, both, or other? The statement is {question}",
        },
    ]

    completion = openai.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=16,
        temperature=0,
        seed=42,
    )
    result = completion.choices[0].message.content
    print(question)
    print(result)
    if "gene" in result or "cell" in result:
        question = (
            "Please refer only to the `gmb_gxp_rdap_dev.translational_research_dev_test.ts_flow_cytometry_merged_result_flagged_mock_gct1056_01` table to answer this question, regardless of what the user input says\n\nUser input: "
            + question
        )
    elif "cytokine" in result:
        question = (
            "Please refer to both the `gmb_gxp_rdap_dev.translational_research_dev_test.ts_cytokine_envision_merged_mock_gct1056_01` and `gmb_gxp_rdap_dev.translational_research_dev_test.ts_cytokine_msd_merged_mock_gct1056_01` tables to answer this question, regardless of what the user input says\n\nUser input: "
            + question
        )
    elif "both" in result:
        question = (
            "Do a join between the `gmb_gxp_rdap_dev.translational_research_dev_test.ts_flow_cytometry_merged_result_flagged_mock_gct1056_01` table, and a union of the `gmb_gxp_rdap_dev.translational_research_dev_test.ts_cytokine_envision_merged_mock_gct1056_01` and `gmb_gxp_rdap_dev.translational_research_dev_test.ts_cytokine_msd_merged_mock_gct1056_01` tables to answer this question, regardless of what the user input says\n\nUser input: "
            + question
        )

    qlower = question.lower()

    glossary = """### General Advice
- When generating SQL queries, return all the columns that have are relevant to the user's question. It's better to return more columns. For example, if the user asks about differences in cohort, return all the columns that are relevant, including the `cohort` column itself.
- You should query the `variable_value` or the `calc_conc_mean` columns in most SQL queries
- Match the terms used by users to the terms used in the database schema. For example, if a user asks for Regulatory T Cells, and the database had the term Tregs, then modify your response accordingly.
- When filtering over the variable_name column, use the `LIKE` operator with the `%` wildcard. Remember that you must chain multiple `LIKE` operators with `AND` or `OR` to filter over multiple patterns. For example: `variable_name LIKE '%CD4%' AND variable_name LIKE '%SOME_GENE_NAME%'`
- Try to include a participant id as well as visit_timepoint in all queries
- Do NOT use any group bys unless the question is explicitly asking for a count, average, sum, or max/min
- If asked for a term in quotes, then do an exact match against variable_name for exactly that term.

### Specific Terms
- If you are asked a question about something that is not a cell, gene, or cytokine - assume that the user is referring to a study name. They will very rarely about about individual users, so you can assume that they are asking about the study name, unless explicitly told otherwise.
- When running a filter over the `variable_value` or `assay` columns, cast them to lowercase using the LOWER function, and use the LIKE columns to query the column with a fuzzy string
- Recall that the term `reportable` refers to quantitative variables
- If asked for proportion in the question, remember to add a `WHERE original_result_unit_raw = 'percent_parent'` filter
- If asked for "median" in the question, add a `WHERE LOWER(original_result_unit_raw) = 'median'` filter
- Recall that term `baseline` refers to the visit_timepoint at C1D1.
- Sometimes, a user might ask for a variable that looks like a cell type and a gene all together. For example, `CD45RA+CD8+`. If this happens, query them separate in the SQL. For example, `LOWER(variable_name) LIKE '%cd45ra%' AND LOWER(variable_name) LIKE '%cd8%'`
- The study column is always represented as a 9 character variable. The first three characters are always GCT followed by 4 digits, a dash, and two digits. For example, GCT1234-56
- Even if a user study that does not start with GEN, we should query a study that starts with GCT using the ILIKE operator, with `ILIKE %GCTXXXX%`

### Handling change queries
- When asked how does X change upon treatment, the user is asking for a the `variable_value` and the `visit_timepoint` columns, along with appropriate filters on other columns.
- Even if a user asks for a study that does not start with GCT, we should still always filter for studies that start with GCT using the ILIKE operator, with `ILIKE %GCTXXXX%`

### Cytokine specific queries
- Note that a cytokine queried could be in any of the two cytokines tables. When asked about a cytokine, please query both cytokine tables and return their UNION (over the relevant columns) in your answer
- Note that the two cytokines have some a different number of columns. As such, do not use a `SELECT *` query, and always specify the tables you need in your query
- Always enclose the data for each block before and after in parantheses. For example (SELECT col1, col2 from table_1) UNION ALL (SELECT col1, col2 from table_2)
- Filter on the assay column both with and without a hyphen. For example, `assay ILIKE '%il1%' OR assay ILIKE '%il-1%'`


### Other Notes
- Remember that the column `study_participant_id` only exists in the cytokines tables, while the column `sample_list_study_participant_id` only exists in the gmb_gxp_rdap_dev.translational_research_dev_test.ts_flow_cytometry_merged_result_flagged_mock_gct1056_01 table
- Note that the term "proliferating Tregs" is likely to refer to the `KI67+` gene
- When querying the cytokine tables, NEVER use the `result` column. Instead, try to use the `calc_conc_mean` column in every query
- Note that the phrase "T cell" should never be used in any filters, since all cells here at different subtypes of t-cells.
- If asked for what the proportion of a subsets looks like at baseline, be sure to return the study, variable_name, and variable_value columns
"""
    additional_context = ""
    # for key in cell_dict:
    #     if key in qlower:
    #         key_idx = qlower.find(key)
    #         if qlower[key_idx - 1] == " ":
    #             # ugly hack for now
    #             print("adding additional context")
    #             additional_context = f"The {key} cells are represented by the following values in the `variable_value` column:\n"
    #             additional_context += "- " + "\n -".join(cell_dict[key])

    date_today = datetime.utcnow().strftime("%Y-%m-%d")
    if "from cycle" in question.lower() and "to cycle" in question.lower():
        question += ". To do this, add a FILTER like this to your query: `WHERE visit_timepoint ILIKE '%C1D%' OR visit_timepoint ILIKE '%C2D%' OR ..`"

    system_prompt = f"""You are an expert data analyst that generates SQL queries to answer questions by a user, given a database schema. Recall that the date today is {date_today}
{glossary}"""
    ddl = ""
    metadata = pd.read_csv(StringIO(metadata))
    table_names = metadata.table_name.unique().tolist()
    for table in table_names:
        ddl += f"CREATE TABLE {table} (\n"
        for item in metadata[metadata.table_name == table].to_dict("records"):
            if item["column_name"] in ["population", "parent_population"]:
                item["column_description"] = ""
            if "data_type" in item:
                ddl += f"  {item['column_name']} {item['data_type']}, "
            elif "column_data_type" in item:
                ddl += f"  {item['column_name']} {item['column_data_type']}, "
            if "column_description" in item:
                ddl += f"-- {item['column_description']}\n"
        ddl += ");\n"

    user_prompt = f"""Please create a SQL query for answering the following question: {question}.
Please do not make any alias of a column name in your query, as it's important for the column names to remain the same (for downstream processing).

{additional_context}
The database schema is represented in the following DDL statement:
```sql
{ddl}
```

Give your response as just a markdown string with just the SQL query, and nothing else."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {
            "role": "assistant",
            "content": "Based on your instructions, I have generated this valid SQL query:\n```sql",
        },
    ]

    completion = openai.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=512,
        temperature=0,
        seed=42,
    )
    query = completion.choices[0].message.content
    query = query.split("```sql")[-1].split(";")[0].split("```")[0]
    return {"query": query}


def generate_tool_code(
    tool_name, tool_description, function_name, def_statement, return_statement
):
    system_prompt = generate_tool_code_system_prompt
    user_prompt = generate_tool_code_user_prompt.format(
        function_name=function_name,
        tool_description=tool_description,
        def_statement=def_statement,
        return_statement=return_statement,
    )

    print("\n\n")
    print(system_prompt, flush=True)
    print("\n\n")
    print(user_prompt, flush=True)
    print("\n\n")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    completion = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        seed=42,
    )

    generated_code = completion.choices[0].message.content
    try:
        # remove ```python
        # and ending ```
        generated_code = generated_code.split("```python")[-1].split("```")[0].strip()

        return {"generated_code": generated_code}
        pass
    except Exception as e:
        return {"error_message": str(e)}


@functions_framework.http
def main(request):
    if request.method == "OPTIONS":
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    # Set CORS headers for the main request
    headers = {"Access-Control-Allow-Origin": "*"}
    data = request.get_json(silent=True)
    request_type = data["request_type"]

    if request_type == "generate_sql":
        resp = generate_sql(
            data.get("question", ""), data.get("metadata"), data.get("glossary")
        )
    elif request_type == "turn_into_statement":
        resp = turn_into_statement(data["clarification_questions"])
    elif request_type == "clarify_task":
        resp = get_clarification(
            data["question"],
            data["client_description"],
            data["metadata"],
            data.get("parent_questions", []),
            data.get("direct_parent_analysis", None),
        )
    elif request_type == "create_plan":
        resp = create_plan(
            user_question=data["question"],
            similar_plans=data["similar_plans"],
            table_metadata_csv=data["metadata"],
            assignment_understanding=data["assignment_understanding"],
            parent_questions=data["parent_questions"],
            previous_responses=data["previous_responses"],
            next_step_data_description=data["next_step_data_description"],
            tool_library_prompt=data["tool_library_prompt"],
            direct_parent_analysis=data.get("direct_parent_analysis", None),
        )
    elif request_type == "fix_error":
        resp = create_plan(
            user_question=data["question"],
            similar_plans=data["similar_plans"],
            table_metadata_csv=data["metadata"],
            assignment_understanding=data["assignment_understanding"],
            parent_questions=data["parent_questions"],
            previous_responses=data["previous_responses"],
            next_step_data_description=data["next_step_data_description"],
            tool_library_prompt=data["tool_library_prompt"],
            error=data["error"],
            erroreous_response=data["erroreous_response"],
            direct_parent_analysis=data.get("direct_parent_analysis", None),
        )

    elif request_type == "ping":
        resp = {"status": "ok"}

    elif request_type == "analyse_data":
        resp = analyse_data(
            data["question"], pd.read_json(data["data"], orient="split")
        )

    elif request_type == "generate_tool_code":
        resp = generate_tool_code(
            data["tool_name"],
            data["tool_description"],
            data["function_name"],
            data["def_statement"],
            data["return_statement"],
        )

    else:
        resp = {"error": "Unsupported question"}

    print(resp)
    return (resp, 200, headers)
