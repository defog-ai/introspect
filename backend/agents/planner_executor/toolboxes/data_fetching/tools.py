import pandas as pd


async def data_fetcher_and_aggregator(
    question: str,
    global_dict: dict = {},
    **kwargs,
):
    """
    This function generates a SQL query and runs it to get the answer.
    """
    import os
    import asyncio
    import pandas as pd
    from tool_code_utilities import safe_sql, fetch_query_into_df
    from defog import Defog
    from utils import SqlExecutionError
    from db_utils import get_db_type_creds

    if question == "" or question is None:
        raise ValueError("Question cannot be empty")

    api_key = global_dict.get("dfg_api_key", "")
    res = get_db_type_creds(api_key)
    db_type, db_creds = res

    dev = global_dict.get("dev", False)
    temp = global_dict.get("temp", False)
    print(f"Dev: {dev}")
    print(f"Global dict currently has keys: {list(global_dict.keys())}")

    # send the data to the Defog, and get a response from it
    defog = Defog(api_key=api_key, db_type=db_type, db_creds=db_creds)
    defog.base_url = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
    defog.generate_query_url = os.environ.get(
        "DEFOG_GENERATE_URL", defog.base_url + "/generate_query_chat"
    )
    # make async request to the url, using the appropriate library
    try:
        res = await asyncio.to_thread(defog.get_query, question, dev=dev, temp=temp)
        query = res["query_generated"]
        print(query)
    except:
        return {
            "error_message": "There was an error in generating the query. Please try again."
        }

    if not safe_sql(query):
        success = False
        print("Unsafe SQL Query")
        return {
            "outputs": [
                {
                    "data": pd.DataFrame(),
                    "analysis": "This was an unsafe query, and hence was not executed",
                }
            ],
            "sql": query.strip(),
        }

    print(f"Running query: {query}")

    try:
        df, sql_query = await fetch_query_into_df(
            api_key=api_key, sql_query=query, temp=temp
        )
    except Exception as e:
        print("Raising execution error", flush=True)
        raise SqlExecutionError(query, str(e))

    analysis = ""
    return {
        "outputs": [{"data": df, "analysis": analysis}],
        "sql": sql_query.strip(),
    }


async def send_email(
    full_data: pd.DataFrame = None,
    email_subject: str = None,
    recipient_email_address: str = None,
    global_dict: dict = {},
    **kwargs,
):
    import resend
    import os

    # convert the full_data into markdown, using the pandas method
    full_data_md = full_data.to_html(index=False)

    resend.api_key = os.environ.get("RESEND_API_KEY")
    params = {
        "from": "support@defog.ai",
        "to": recipient_email_address,
        "subject": email_subject,
        "html": f"You can find your analysis below:<br/><br/>{full_data_md}",
    }
    resend.Emails.send(params)
    return {
        "outputs": [
            {
                "data": pd.DataFrame(
                    [
                        [
                            {
                                "message": f"Email sent successfully to {recipient_email_address}"
                            },
                        ]
                    ]
                ),
                "analysis": "Email sent successfully",
            }
        ],
    }
