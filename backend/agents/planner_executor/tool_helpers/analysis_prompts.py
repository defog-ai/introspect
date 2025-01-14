# these prompts are used if users are using a non defog model for analyzing data

#####################
# BEDROCK
#####################
DEFAULT_BEDROCK_MODEL = "meta.llama3-70b-instruct-v1:0"

DEFAULT_BEDROCK_PROMPT = """<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Can you please give me the high-level trends (as bullet points that start with a hyphen) of data in a CSV? Note that this CSV was generated to answer the question: `{question}`

This was the SQL query used to generate the table:
{sql}

This was the data generated:
{data_csv}

Do not use too much math in your analysis. Just tell me, at a high level, what the key insights are. Give me the trends as bullet points. No preamble or anything else.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

Here is a summary of the high-level trends in the data:
"""

#####################
# OpenAI
#####################
DEFAULT_OPENAI_MODEL = "gpt-4o"

DEFAULT_OPENAI_SYSTEM_PROMPT = "You are a data scientist. You have been given a CSV file with data. You need to analyze the data and provide a summary of the key insights. Please make sure that the summary is concise and to the point, and that you do not make any factual errors."

DEFAULT_OPENAI_USER_PROMPT = """A user asked me the question `{question}`. I created the following CSV file to answer the question:
```csv
{data_csv}
```

I also ran the following SQL query to generate the data for this CSV:
```sql
{sql}
```

Please analyze the data in the CSV file and provide a summary of the key insights. Make sure that the summary is concise and to the point, and that you do not make any factual errors. Please give rich, narrative insights that are easy to understand. Do not use too much math in your analysis. Just tell me, at a high level, what the key insights are.

Return the insights as a markdown block."""
