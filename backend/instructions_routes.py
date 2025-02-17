from auth_utils import validate_user_request
from fastapi import APIRouter, Depends
from request_models import InstructionsUpdateRequest, UserRequest
from utils_instructions import get_instructions, set_instructions

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Instructions Management"],
)


@router.post("/integration/get_instructions")
async def get_instructions_route(request: UserRequest):
    instructions = await get_instructions(db_name=request.db_name)
    return {"instructions": instructions}


@router.post("/integration/update_instructions")
async def update_instructions_route(request: InstructionsUpdateRequest):
    await set_instructions(
        db_name=request.db_name, instructions_text=request.instructions
    )
    return {"success": True}
