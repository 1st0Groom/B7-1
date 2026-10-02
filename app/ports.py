"""Small contracts used by chat orchestration; no HTTP, ORM or provider SDK imports."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


@dataclass(frozen=True)
class TurnRecord:
    id: int
    conversation_id: int
    client_request_id: str
    question: str
    answer: str | None
    status: Literal["pending", "succeeded", "failed"]
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class Reservation:
    turn: TurnRecord
    created: bool


class StorageError(Exception):
    """Persistence could not confirm the operation's outcome."""


class ReplyGenerator(Protocol):
    async def generate(self, history: list[tuple[str, str]], question: str) -> str:
        """Return a nonempty answer, or raise AppError with a safe provider error code."""
        ...


class AIProvider(ReplyGenerator, Protocol):
    async def close(self) -> None: ...


class ChatPolicy(Protocol):
    @property
    def chat_context_turns(self) -> int: ...

    @property
    def ai_timeout_seconds(self) -> float: ...

    @property
    def ai_model(self) -> str: ...


class ChatStore(Protocol):
    async def reserve(
        self,
        user_id: int,
        conversation_id: int,
        question: str,
        request_id: str,
        admit: Callable[[], None],
    ) -> Reservation:
        """Check ownership, replay existing keys, or commit a new pending turn.

        Call admit only for a new request. Enforce one pending turn per conversation.
        No transaction may remain open after returning.
        """
        ...

    async def history(self, turn: TurnRecord, limit: int) -> list[tuple[str, str]]:
        """Return earlier successful pairs in chronological order."""
        ...

    async def finish(
        self,
        turn_id: int,
        *,
        answer: str | None = None,
        error_code: str | None = None,
        model: str | None = None,
        latency_ms: int | None = None,
    ) -> TurnRecord:
        """Commit pending -> terminal, returning the persisted winner of a race."""
        ...


class PendingRecovery(Protocol):
    async def recover_pending(self, *, all_pending: bool = False) -> None: ...
