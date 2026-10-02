"""Chat use case: admission, generation and persisted outcomes through small ports."""

import asyncio
import time
from collections.abc import Callable

from app.errors import AppError
from app.logging import event
from app.ports import ChatPolicy, ChatStore, ReplyGenerator, StorageError, TurnRecord


def replay(turn: TurnRecord, question: str) -> TurnRecord:
    if turn.question != question:
        raise AppError("IDEMPOTENCY_CONFLICT", 409, turn.id)
    if turn.status == "pending":
        raise AppError("CHAT_IN_PROGRESS", 409, turn.id)
    if turn.status == "failed":
        raise AppError(turn.error_code, turn_id=turn.id)
    return turn


class ChatService:
    def __init__(
        self,
        store: ChatStore,
        ai: ReplyGenerator,
        policy: ChatPolicy,
        admit: Callable[[int], None],
    ):
        self.store = store
        self.ai = ai
        self.policy = policy
        self.admit = admit

    async def send(
        self,
        user_id: int,
        conversation_id: int,
        question: str,
        request_id: str,
    ) -> TurnRecord:
        try:
            return await self._send(user_id, conversation_id, question, request_id)
        except StorageError:
            raise AppError("DB_UNAVAILABLE") from None

    async def _send(
        self,
        user_id: int,
        conversation_id: int,
        question: str,
        request_id: str,
    ) -> TurnRecord:
        reservation = await self.store.reserve(
            user_id, conversation_id, question, request_id, lambda: self.admit(user_id)
        )
        turn = reservation.turn
        if not reservation.created:
            return replay(turn, question)
        start = time.monotonic()
        try:
            history = await self.store.history(turn, self.policy.chat_context_turns)
            event(
                "ai_call_start", user_id=user_id, conversation_id=conversation_id, turn_id=turn.id
            )
            async with asyncio.timeout(self.policy.ai_timeout_seconds):
                answer = await self.ai.generate(history, question)
            event(
                "ai_call_success",
                turn_id=turn.id,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
        except asyncio.CancelledError:
            try:
                await asyncio.shield(self.store.finish(turn.id, error_code="REQUEST_INTERRUPTED"))
            except StorageError:
                event("db_save_failed", phase="interrupted", turn_id=turn.id)
            raise
        except Exception as exc:
            if isinstance(exc, TimeoutError):
                code = "AI_TIMEOUT"
            elif isinstance(exc, AppError):
                code = exc.code
            elif isinstance(exc, StorageError):
                code = "DB_UNAVAILABLE"
            else:
                code = "INTERNAL_ERROR"
            event("ai_call_failed", turn_id=turn.id, code=code)
            saved = await self.store.finish(turn.id, error_code=code)
        else:
            saved = await self.store.finish(
                turn.id,
                answer=answer,
                model=self.policy.ai_model,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
        # Recovery can win while generation is in flight; the persisted outcome is authoritative.
        return replay(saved, question)
