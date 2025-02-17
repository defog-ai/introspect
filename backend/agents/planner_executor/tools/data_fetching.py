import pandas as pd


async def data_fetcher_and_aggregator(
    question: str,
    db_name: str,
    hard_filters: list = [],
    previous_context: list = [],
    **kwargs,
):
    """
    This function generates a SQL query and runs it to get the answer.

    IMPORTANT NOTE: Changing this function directly will NOT change the behavior of the tool immediately. You will have to rebuild the docker image to see changes in effect. This is because the tool code is compiled into a string that lives inside a postgres database, and that code string is then run to execute the tool.
    """
    import pandas as pd
    from tool_code_utilities import fetch_query_into_df
    from utils import SqlExecutionError
    from db_utils import get_db_type_creds
    from utils_sql import safe_sql, generate_sql_query

    if question == "" or question is None:
        raise ValueError("Question cannot be empty")

    res = await get_db_type_creds(db_name)
    db_type, _ = res

    print(f"Previous context: {previous_context}", flush=True)

    # generate SQL
    res = await generate_sql_query(
        question=question,
        db_name=db_name,
        db_type=db_type,
        hard_filters=hard_filters,
        previous_context=previous_context,
    )

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
        }

    print(f"Running query: {query}")

    try:
        df, sql_query = await fetch_query_into_df(
            db_name=db_name,
            sql_query=query,
            question=question,
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
    api_key: str = None,
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
