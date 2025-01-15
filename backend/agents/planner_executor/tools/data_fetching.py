import pandas as pd


async def data_fetcher_and_aggregator(
    question: str,
    hard_filters: list = [],
    global_dict: dict = {},
    previous_context: list = [],
    **kwargs,
):
    """
    This function generates a SQL query and runs it to get the answer.

    IMPORTANT NOTE: Changing this function directly will NOT change the behavior of the tool immediately. You will have to rebuild the docker image to see changes in effect. This is because the tool code is compiled into a string that lives inside a postgres database, and that code string is then run to execute the tool.
    """
    import os
    import pandas as pd
    from generic_utils import make_request
    from tool_code_utilities import safe_sql, fetch_query_into_df
    from utils import SqlExecutionError
    from db_utils import get_db_type_creds

    if question == "" or question is None:
        raise ValueError("Question cannot be empty")

    api_key = global_dict.get("dfg_api_key", "")
    res = await get_db_type_creds(api_key)
    db_type, _ = res

    temp = global_dict.get("temp", False)
    print(f"Global dict currently has keys: {list(global_dict.keys())}")
    print(f"Previous context: {previous_context}", flush=True)

    # send the data to the Defog, and get a response from it
    generate_query_url = os.environ.get(
        "DEFOG_GENERATE_URL",
        os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")
        + "/generate_query_chat",
    )
    # make async request to the url, using the appropriate library
    res = await make_request(
        url=generate_query_url,
        data={
            "api_key": api_key,
            "question": question,
            "hard_filters": hard_filters,
            "previous_context": previous_context,
            "db_type": db_type,
        },
    )
    print(generate_query_url, flush=True)

    reference_queries = res.get("reference_queries", [])
    instructions_used = res.get("pruned_instructions", "")
    query = res.get("sql")

    if query is None:
        return {
            "error_message": f"There was an error in generating the query. The error was: {res.get('error')}",
        }

    if not safe_sql(query):
        print("Unsafe SQL Query")
        return {
            "outputs": [
                {
                    "data": pd.DataFrame(),
                    "analysis": "This was an unsafe query, and hence was not executed",
                }
            ],
            "sql": query.strip(),
            "reference_queries": reference_queries,
            "instructions_used": instructions_used,
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
        "reference_queries": reference_queries,
        "instructions_used": instructions_used,
    }


async def send_email(
    full_data: pd.DataFrame = None,
    email_subject: str = None,
    recipient_email_address: str = None,
    global_dict: dict = {},
    **kwargs,
):
    """
    This tool is used to send email.
    """
    import os

    success = False

    EMAIL_OPTION = os.environ.get("EMAIL_OPTION", "DEFOG")

    if EMAIL_OPTION == "RESEND":
        import resend

        # convert the full_data into markdown, using the pandas method
        full_data_md = full_data.head(50).to_html(index=False)

        resend.api_key = os.environ.get("RESEND_API_KEY")
        if os.environ.get("FROM_EMAIL") is None:
            raise ValueError("FROM_EMAIL is not set in the environment variables")
        params = {
            "from": os.environ.get("FROM_EMAIL"),
            "to": recipient_email_address,
            "subject": email_subject,
            "html": f"You can find the table answering your question asked (first 50 rows) below:<br/><br/>{full_data_md}",
        }
        resend.Emails.send(params)
        success = True
    elif EMAIL_OPTION == "SES":
        import boto3

        ses = boto3.client(
            "ses", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )

        # convert the full_data into markdown, using the pandas method
        full_data_md = full_data.head(50).to_html(index=False)

        response = ses.send_email(
            Destination={"ToAddresses": [recipient_email_address]},
            Message={
                "Body": {
                    "Text": {
                        "Charset": "UTF-8",
                        "Data": f"Please open this email in an HTML supported email client to see the data.",
                    },
                    "Html": {
                        "Charset": "UTF-8",
                        "Data": f"You can find the table answering your question asked (first 50 rows) below:<br/><br/>{full_data_md}",
                    },
                },
                "Subject": {"Charset": "UTF-8", "Data": email_subject},
            },
            Source=os.environ.get("FROM_EMAIL"),
        )
        success = True
    elif EMAIL_OPTION == "DEFOG":
        import httpx

        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(
                url=os.getenv("DEFOG_BASE_URL", "https://api.defog.ai")
                + "/email_data_report",
                json={
                    "api_key": global_dict.get("dfg_api_key"),
                    "to_email": recipient_email_address,
                    "subject": email_subject,
                    "data_csv": full_data.to_csv(index=False),
                },
                timeout=300,
            )
            if r.status_code == 200:
                success = True
            else:
                success = False

    if success:
        message = f"Email sent successfully to {recipient_email_address}"
    else:
        message = f"Email could not be successfully sent to {recipient_email_address}."

    return {
        "outputs": [
            {
                "data": pd.DataFrame(
                    [
                        [
                            {"message": message},
                        ]
                    ]
                ),
                "analysis": message,
            }
        ],
    }
