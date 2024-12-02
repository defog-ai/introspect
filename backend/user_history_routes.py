from fastapi import APIRouter, Request
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
    username = validate_user(token, get_username=True)
    if not username:
        return {"error": "Invalid token"}
    
    with engine.begin() as conn:
        user_history = conn.execute(select(UserHistory).where(UserHistory.username == username)).fetchone()
    
    if user_history:
        return {"history": user_history.history}
    else:
        return {"history": None}

@router.post("/update_user_history")
async def update_user_history(request: Request):
    params = await request.json()
    token = params.get("token")
    username = validate_user(token, get_username=True)
    if not username:
        return {"error": "Invalid token"}
    
    history = params.get("history")

    if history is None or history == {}:
        return {"error": "History is required"}
    
    for key in history:
        if not isinstance(history[key], dict):
            return {"error": "History must be a dictionary of dictionaries"}
        if history[key] == {}:
            return {"error": "History cannot contain empty dictionaries"}

    
    with engine.begin() as conn:
        # Check if history exists for user
        existing_history = conn.execute(
            select(UserHistory).where(UserHistory.username == username)
        ).fetchone()
        
        if existing_history:
            # Update existing history
            conn.execute(
                update(UserHistory)
                .where(UserHistory.username == username)
                .values(history=history)
            )
        else:
            # Create new history entry
            conn.execute(
                insert(UserHistory).values(
                    username=username,
                    history=history
                )
            )
    
    return {"message": "User history updated"}

@router.post("/clear_user_history")
async def clear_user_history(request: Request):
    params = await request.json()
    token = params.get("token")
    username = validate_user(token, get_username=True)
    if not username:
        return {"error": "Invalid token"}
    
    with engine.begin() as conn:
        conn.execute(
            update(UserHistory)
            .where(UserHistory.username == username)
            .values(history={})
        )
    
    return {"message": "User history cleared"}