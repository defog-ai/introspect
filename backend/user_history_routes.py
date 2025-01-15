from fastapi import APIRouter, Request
from pydantic import BaseModel
from utils_logging import LOGGER
from db_utils import UserHistory, validate_user, engine
from sqlalchemy import (
    select,
    update,
    insert,
)


router = APIRouter()


@router.post("/get_user_history")
async def get_user_history(request: Request):
    params = await request.json()
    token = params.get("token")
    username = await validate_user(token, get_username=True)
    if not username:
        return {"error": "Invalid token"}

    with engine.begin() as conn:
        user_history = conn.execute(
            select(UserHistory).where(UserHistory.username == username)
        ).fetchone()

    if user_history:
        return {"history": user_history.history}
    else:
        return {"history": None}


class UpdateHistoryRequest(BaseModel):
    token: str
    key_name: str
    history: dict

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "user_token",
                    "key_name": "history_key",
                    "history": {"data": "history_data"}
                }
            ]
        }
    }


@router.post("/update_user_history")
async def update_user_history(request: UpdateHistoryRequest):
    token = request.token
    username = await validate_user(token, get_username=True)
    key_name = request.key_name
    history = request.history

    if not key_name:
        return {"error": "Invalid key name."}

    if not username:
        return {"error": "Invalid token"}

    if history is None:
        history = {}

    with engine.begin() as conn:
        # Check if history exists for user
        existing_history = conn.execute(
            select(UserHistory).where(UserHistory.username == username)
        ).fetchone()

        if existing_history:
            new_history = existing_history._mapping["history"]
            new_history[key_name] = history
            # Update existing history
            conn.execute(
                update(UserHistory)
                .where(UserHistory.username == username)
                .values(history=new_history)
            )
        else:
            # Create new history entry
            LOGGER.debug(
                f"creating new history item for user: {username} and key name: {key_name}"
            )
            conn.execute(
                insert(UserHistory).values(
                    username=username, history={key_name: history}
                )
            )

    return {"message": "User history updated"}
