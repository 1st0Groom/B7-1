"""Question → AI call → answer → chat log, with recent exchanges as context."""

import time

from sqlalchemy import select

from app.database import commit
from app.errors import AppError
from app.logging import event
from app.models import Chat
from app.services import rate_limit

CONTEXT_TURNS = 5
CONTEXT_MAX_CHARS = 4000


def trim_context(context):
    """Drop the oldest exchanges until the context fits in CONTEXT_MAX_CHARS."""
    total = sum(len(q) + len(a) for q, a in context)
    while context and total > CONTEXT_MAX_CHARS:
        q, a = context.pop(0)
        total -= len(q) + len(a)
    return context


async def history(db, user_id):
    async with db.sessions() as session:
        rows = await session.scalars(select(Chat).where(Chat.user_id == user_id).order_by(Chat.id))
        return list(rows)


async def ask(db, ai, user_id, question):
    if not rate_limit.allow(user_id):
        event("chat_rate_limited", user_id=user_id)
        raise AppError("CHAT_RATE_LIMITED")
    async with db.sessions() as session:
        recent = await session.scalars(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.id.desc())
            .limit(CONTEXT_TURNS)
        )
        context = trim_context([(chat.question, chat.answer) for chat in reversed(list(recent))])
    event("ai_call_start", user_id=user_id, context_turns=len(context))
    start = time.monotonic()
    try:
        answer = await ai.generate(context, question)
    except AppError as exc:
        event(
            "ai_call_failed",
            user_id=user_id,
            code=exc.code,
            latency_ms=int((time.monotonic() - start) * 1000),
        )
        raise
    event("ai_call_success", user_id=user_id, latency_ms=int((time.monotonic() - start) * 1000))
    async with db.sessions() as session:
        chat = Chat(user_id=user_id, question=question, answer=answer)
        session.add(chat)
        await commit(session, phase="chat", user_id=user_id)
        return chat
