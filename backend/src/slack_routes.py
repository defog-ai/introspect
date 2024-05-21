from fastapi import APIRouter, Request
import os
from slack_sdk.web.async_client import AsyncWebClient
from auth_utils import validate_user_email
import re

slack_client = AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])
router = APIRouter()

from defog import Defog
import pandas as pd
import asyncio


@router.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    if "challenge" in data:
        return {"challenge": data["challenge"]}

    event = data["event"]

    # process event in background
    asyncio.create_task(process_event(event))
    return {"status": "ok"}


async def process_event(event):
    if "text" in event and "bot_id" not in event:
        try:
            channel_id = event["channel"]
            user_query = event["text"]
            user_query = re.sub(r"<@(\w+)>", "", user_query).strip()

            user_id = event["user"]
            user_dets = await slack_client.users_info(user=user_id)
            user_email = user_dets["user"]["profile"]["email"]

            if not validate_user_email(user_email):
                await slack_client.chat_postMessage(
                    channel=channel_id,
                    text=f"You are not authorized to use this app. Please contact the administrator if you would like access, and ask for the email `{user_email}` to be added to the system.",
                )
            else:
                defog = Defog()
                res = await asyncio.to_thread(defog.run_query, user_query)
                df = pd.DataFrame(res["data"], columns=res["columns"])

                # convert df into markdown table
                table = df.to_csv(index=False)

                await slack_client.files_upload_v2(
                    channel=channel_id,
                    title=f"Result for question {user_query}",
                    filename=f"result_{user_query}.csv",
                    content=table,
                    initial_comment=f"This is a table that answers the question `{user_query}`.\nThe SQL query used to answer this is below:\n\n```\n{res['query_generated']}\n```",
                )
        except Exception as e:
            print(e, flush=True)
            await slack_client.chat_postMessage(
                channel=channel_id,
                text="An error occurred while processing the query. Please try again. Here is the full error message:\n\n```"
                + str(e)
                + "```",
            )
    else:
        print("Ignoring event", flush=True)
