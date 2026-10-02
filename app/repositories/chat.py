"""SQLAlchemy persistence, transaction boundaries and race-safe writes for chat."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import Database, commit
from app.errors import AppError
from app.models import ChatTurn, Conversation, utcnow
from app.ports import Reservation, StorageError, TurnRecord
from app.repositories.conversations import owned_conversation


def record(turn: ChatTurn) -> TurnRecord:
    return TurnRecord(**{name: getattr(turn, name) for name in TurnRecord.__dataclass_fields__})


class SQLAlchemyChatStore:
    def __init__(self, db: Database):
        self.db = db

    @asynccontextmanager
    async def session(self):
        try:
            async with self.db.sessions() as session:
                yield session
        except SQLAlchemyError as exc:
            raise StorageError() from exc

    async def reserve(
        self,
        user_id: int,
        conversation_id: int,
        question: str,
        request_id: str,
        admit: Callable[[], None],
    ) -> Reservation:
        async with self.session() as session:
            conversation = await owned_conversation(session, user_id, conversation_id)
            existing = await session.scalar(
                select(ChatTurn).where(
                    ChatTurn.conversation_id == conversation_id,
                    ChatTurn.client_request_id == request_id,
                )
            )
            if existing:
                return Reservation(record(existing), created=False)
            if await session.scalar(
                select(ChatTurn.id).where(
                    ChatTurn.conversation_id == conversation_id, ChatTurn.status == "pending"
                )
            ):
                raise AppError("CHAT_IN_PROGRESS", 409)
            admit()
            first_turn = not await session.scalar(
                select(ChatTurn.id).where(ChatTurn.conversation_id == conversation_id).limit(1)
            )
            turn = ChatTurn(
                conversation_id=conversation_id, client_request_id=request_id, question=question
            )
            session.add(turn)
            conversation.updated_at = utcnow()
            if first_turn:
                conversation.title = question[:30]
            try:
                await commit(
                    session, phase="question", user_id=user_id, conversation_id=conversation_id
                )
            except IntegrityError:
                existing = await session.scalar(
                    select(ChatTurn).where(
                        ChatTurn.conversation_id == conversation_id,
                        ChatTurn.client_request_id == request_id,
                    )
                )
                if existing:
                    return Reservation(record(existing), created=False)
                raise AppError("CHAT_IN_PROGRESS", 409) from None
        return Reservation(record(turn), created=True)

    async def history(self, turn: TurnRecord, limit: int) -> list[tuple[str, str]]:
        async with self.session() as session:
            previous = list(
                (
                    await session.scalars(
                        select(ChatTurn)
                        .where(
                            ChatTurn.conversation_id == turn.conversation_id,
                            ChatTurn.status == "succeeded",
                            ChatTurn.id < turn.id,
                        )
                        .order_by(ChatTurn.id.desc())
                        .limit(limit)
                    )
                ).all()
            )
        return [(item.question, item.answer) for item in reversed(previous)]

    async def finish(self, turn_id, *, answer=None, error_code=None, model=None, latency_ms=None):
        async with self.session() as session:
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
            return record(turn)

    async def recover_pending(self, *, all_pending=False):
        async with self.session() as session:
            query = update(ChatTurn).where(ChatTurn.status == "pending")
            if not all_pending:
                query = query.where(ChatTurn.created_at < utcnow() - timedelta(seconds=90))
            result = await session.execute(
                query.values(
                    status="failed", error_code="REQUEST_INTERRUPTED", completed_at=utcnow()
                )
            )
            if result.rowcount:
                await commit(session, phase="recovery", count=result.rowcount)
            else:
                await session.rollback()
