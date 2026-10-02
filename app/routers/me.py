from fastapi import APIRouter, Query

from app.dependencies import AuthUser, DatabaseDep
from app.repositories import conversations
from app.schemas import TurnList, UserOutput

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
    return await conversations.user_history(db, user.id, limit, before_id)
