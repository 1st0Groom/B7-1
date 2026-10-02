from fastapi import APIRouter, Query

from app.dependencies import AuthUser, ChatServiceDep, DatabaseDep, RateLimiterDep
from app.repositories import conversations
from app.schemas import (
    ConversationList,
    ConversationOutput,
    EmptyInput,
    MessageInput,
    TurnList,
    TurnOutput,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", status_code=201, response_model=ConversationOutput)
async def create_conversation(
    data: EmptyInput, user: AuthUser, db: DatabaseDep, limiter: RateLimiterDep
):
    limiter.check(("conversation", user.id), limit=30)
    return await conversations.create(db, user.id)


@router.get("", response_model=ConversationList)
async def list_conversations(
    user: AuthUser,
    db: DatabaseDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    rows = await conversations.list_for_user(db, user.id, limit, offset)
    return {"items": rows, "limit": limit, "offset": offset}


@router.get("/{conversation_id}/turns", response_model=TurnList)
async def list_turns(
    conversation_id: int,
    user: AuthUser,
    db: DatabaseDep,
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, ge=1),
):
    return await conversations.history(db, user.id, conversation_id, limit, before_id)


@router.post("/{conversation_id}/messages", response_model=TurnOutput)
async def message(
    conversation_id: int,
    data: MessageInput,
    user: AuthUser,
    chat: ChatServiceDep,
):
    return await chat.send(user.id, conversation_id, data.question, str(data.client_request_id))
