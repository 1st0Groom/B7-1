"""Conversation creation, ownership and paginated history queries."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Database, commit
from app.errors import AppError
from app.models import ChatTurn, Conversation


@dataclass
class TurnPage:
    items: list[ChatTurn]
    next_before_id: int | None


async def owned_conversation(
    session: AsyncSession, user_id: int, conversation_id: int
) -> Conversation:
    conversation = await session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )
    if not conversation:
        raise AppError("CONVERSATION_NOT_FOUND", 404)
    return conversation


async def create(db: Database, user_id: int) -> Conversation:
    async with db.sessions() as session:
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        await commit(session, phase="conversation", user_id=user_id)
        return conversation


async def list_for_user(db: Database, user_id: int, limit: int, offset: int) -> list[Conversation]:
    async with db.sessions() as session:
        rows = await session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows)


async def _turn_page(session, query, limit, before_id) -> TurnPage:
    if before_id is not None:
        query = query.where(ChatTurn.id < before_id)
    rows = list((await session.scalars(query.order_by(ChatTurn.id.desc()).limit(limit + 1))).all())
    items = rows[:limit]
    return TurnPage(items, items[-1].id if len(rows) > limit else None)


async def history(
    db: Database, user_id: int, conversation_id: int, limit: int, before_id: int | None
) -> TurnPage:
    async with db.sessions() as session:
        await owned_conversation(session, user_id, conversation_id)
        page = await _turn_page(
            session,
            select(ChatTurn).where(ChatTurn.conversation_id == conversation_id),
            limit,
            before_id,
        )
        page.items.reverse()  # The chat screen reads each page in chronological order.
        return page


async def user_history(db: Database, user_id: int, limit: int, before_id: int | None) -> TurnPage:
    async with db.sessions() as session:
        query = select(ChatTurn).join(Conversation).where(Conversation.user_id == user_id)
        return await _turn_page(session, query, limit, before_id)
