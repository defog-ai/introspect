from .data_fetching import data_fetcher_and_aggregator, send_email

import inspect

tools = {
    "data_fetcher_and_aggregator": {
        "function_name": "data_fetcher_and_aggregator",
        "tool_name": "Fetch data from database",
        "description": "Converting a natural language question into a SQL query, that then runs on an external database. Fetches, joins, filters, aggregates, and performs arithmetic computations on data. Remember that this tool does not have access to the data returned by the previous steps. It only has access to the data in the database. We should attempt to give this tool very specific questions that pertain to the user question, instead of overly broad or generic ones. However, do not make any mention of which table to query when you give it your question. You can use this exactly once among all steps.",
        "fn": data_fetcher_and_aggregator,
        "code": inspect.getsource(data_fetcher_and_aggregator),
        "input_metadata": {
            "question": {
                "name": "question",
                "default": None,
                "description": "natural language description of the data required to answer this question (or get the required information for subsequent steps) as a string",
                "type": "str",
            },
            "hard_filters": {
                "name": "hard_filters",
                "default": [],
                "description": "List of hard filters to apply to the data",
                "type": "list",
            }
        },
        "output_metadata": [
            {
                "name": "output_df",
                "description": "pandas dataframe",
                "type": "pandas.core.frame.DataFrame",
            }
        ],
    },
    "send_email": {
        "function_name": "send_email",
        "tool_name": "Send Email",
        "description": "This function sends a full dataframe from a preceding step as an email to the specified recipient. It should be used at the end of the analysis, and only once. The recipient email address should be provided as a string, and the dataframe that has to be emailed should be provided as global_dict.<input_df_name>.",
        "fn": send_email,
        "code": inspect.getsource(send_email),
        "input_metadata": {
            "recipient_email_address": {
                "name": "recipient_email_address",
                "default": None,
                "description": "email address of the recipient",
                "type": "str",
            },
            "email_subject": {
                "name": "email_subject",
                "default": None,
                "description": "Title of the email to be sent. This is usually a descriptive summary of the question asked.",
                "type": "str",
            },
            "full_data": {
                "name": "full_data",
                "default": None,
                "description": "global_dict.<input_df_name>",
                "type": "pandas.core.frame.DataFrame",
            },
        },
        "output_metadata": [
            {
                "name": "output_df",
                "description": "pandas dataframe",
                "type": "pandas.core.frame.DataFrame",
            }
        ],
    },
}
