import asyncio
import time
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import commit
from app.errors import AppError
from app.logging import event
from app.models import ChatTurn, Conversation, utcnow
from app.services.conversations import owned_conversation


def replay(turn, question):
    if turn.question != question:
        raise AppError("IDEMPOTENCY_CONFLICT", 409, turn.id)
    if turn.status == "pending":
        raise AppError("CHAT_IN_PROGRESS", 409, turn.id)
    if turn.status == "failed":
        raise AppError(turn.error_code, turn_id=turn.id)
    return turn


async def finish(db, turn_id, *, answer=None, error_code=None, model=None, latency_ms=None):
    async with db.sessions() as session:
        await session.execute(
            update(ChatTurn)
            .where(ChatTurn.id == turn_id, ChatTurn.status == "pending")
            .values(
                status="failed" if error_code else "succeeded",
                answer=answer,
                error_code=error_code,
                completed_at=utcnow(),
                model=model,
                latency_ms=latency_ms,
            )
        )
        turn = await session.get(ChatTurn, turn_id)
        await session.execute(
            update(Conversation)
            .where(Conversation.id == turn.conversation_id)
            .values(updated_at=utcnow())
        )
        await commit(session, phase="result", turn_id=turn_id, status=turn.status)
        return turn


async def recover_pending(db, *, all_pending=False):
    async with db.sessions() as session:
        query = update(ChatTurn).where(ChatTurn.status == "pending")
        if not all_pending:
            query = query.where(ChatTurn.created_at < utcnow() - timedelta(seconds=90))
        result = await session.execute(
            query.values(status="failed", error_code="REQUEST_INTERRUPTED", completed_at=utcnow())
        )
        if result.rowcount:
            await commit(session, phase="recovery", count=result.rowcount)
        else:
            await session.rollback()


async def send_message(db, ai, settings, limiter, user_id, conversation_id, data):
    key = str(data.client_request_id)
    async with db.sessions() as session:
        conversation = await owned_conversation(session, user_id, conversation_id)
        existing = await session.scalar(
            select(ChatTurn).where(
                ChatTurn.conversation_id == conversation_id, ChatTurn.client_request_id == key
            )
        )
        if existing:
            return replay(existing, data.question)
        if await session.scalar(
            select(ChatTurn.id).where(
                ChatTurn.conversation_id == conversation_id, ChatTurn.status == "pending"
            )
        ):
            raise AppError("CHAT_IN_PROGRESS", 409)
        limiter.check(("chat", user_id))
        first_turn = not await session.scalar(
            select(ChatTurn.id).where(ChatTurn.conversation_id == conversation_id).limit(1)
        )
        turn = ChatTurn(
            conversation_id=conversation_id, client_request_id=key, question=data.question
        )
        session.add(turn)
        conversation.updated_at = utcnow()
        if first_turn:
            conversation.title = data.question[:30]
        try:
            await commit(
                session, phase="question", user_id=user_id, conversation_id=conversation_id
            )
        except IntegrityError:
            existing = await session.scalar(
                select(ChatTurn).where(
                    ChatTurn.conversation_id == conversation_id, ChatTurn.client_request_id == key
                )
            )
            if existing:
                return replay(existing, data.question)
            raise AppError("CHAT_IN_PROGRESS", 409) from None
    # No session/transaction stays open while waiting for the provider.
    start = time.monotonic()
    try:
        async with db.sessions() as session:
            previous = list(
                (
                    await session.scalars(
                        select(ChatTurn)
                        .where(
                            ChatTurn.conversation_id == conversation_id,
                            ChatTurn.status == "succeeded",
                            ChatTurn.id < turn.id,
                        )
                        .order_by(ChatTurn.id.desc())
                        .limit(settings.chat_context_turns)
                    )
                ).all()
            )
        history = [(t.question, t.answer) for t in reversed(previous)]
        event("ai_call_start", user_id=user_id, conversation_id=conversation_id, turn_id=turn.id)
        async with asyncio.timeout(settings.ai_timeout_seconds):
            answer = await ai.generate(history, data.question)
        event("ai_call_success", turn_id=turn.id, latency_ms=int((time.monotonic() - start) * 1000))
    except asyncio.CancelledError:
        try:
            await asyncio.shield(finish(db, turn.id, error_code="REQUEST_INTERRUPTED"))
        except SQLAlchemyError:
            event("db_save_failed", phase="interrupted", turn_id=turn.id)
        raise
    except Exception as exc:
        if isinstance(exc, TimeoutError):
            error = AppError("AI_TIMEOUT", turn_id=turn.id)
        elif isinstance(exc, AppError):
            error = AppError(exc.code, exc.status, turn.id)
        elif isinstance(exc, SQLAlchemyError):
            error = AppError("DB_UNAVAILABLE", turn_id=turn.id)
        else:
            error = AppError("INTERNAL_ERROR", turn_id=turn.id)
        event("ai_call_failed", turn_id=turn.id, code=error.code)
        try:
            saved = await finish(db, turn.id, error_code=error.code)
        except SQLAlchemyError:
            raise AppError("DB_UNAVAILABLE", turn_id=turn.id) from None
        # Recovery may have won the race; always return the persisted outcome.
        return replay(saved, data.question)
    try:
        saved = await finish(
            db,
            turn.id,
            answer=answer,
            model=settings.ai_model,
            latency_ms=int((time.monotonic() - start) * 1000),
        )
    except SQLAlchemyError:
        raise AppError("DB_UNAVAILABLE", turn_id=turn.id) from None
    return replay(saved, data.question)
