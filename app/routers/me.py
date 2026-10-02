from fastapi import APIRouter, Query

from app.dependencies import AuthUser, DatabaseDep
from app.schemas import TurnList, UserOutput, turn_json
from app.services import conversations

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOutput)
async def me(user: AuthUser):
    return {"id": user.id, "username": user.username}


@router.get("/chats", response_model=TurnList)
async def my_chats(
    user: AuthUser,
    db: DatabaseDep,
    limit: int = Query(20, ge=1, le=100),
    before_id: int | None = Query(None, ge=1),
):
    page = await conversations.user_history(db, user.id, limit, before_id)
    return {"items": [turn_json(t) for t in page.items], "next_before_id": page.next_before_id}
