"""The same observable chat contract holds for SQL storage and an in-memory substitute."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.errors import AppError
from app.ports import ChatStore, Reservation, StorageError, TurnRecord
from app.repositories.chat import SQLAlchemyChatStore
from app.services.chat import ChatService
from tests.conftest import FakeAI, conversation, register


class MemoryStore:
    def __init__(self):
        self.turns = {}

    async def reserve(self, user_id, conversation_id, question, request_id, admit):
        if user_id != 1 or conversation_id != 1:
            raise AppError("CONVERSATION_NOT_FOUND", 404)
        for turn in self.turns.values():
            if turn.client_request_id == request_id:
                return Reservation(turn, False)
        if any(turn.status == "pending" for turn in self.turns.values()):
            raise AppError("CHAT_IN_PROGRESS", 409)
        admit()
        turn = TurnRecord(
            len(self.turns) + 1,
            conversation_id,
            request_id,
            question,
            None,
            "pending",
            None,
            datetime.now(UTC),
            None,
        )
        self.turns[turn.id] = turn
        return Reservation(turn, True)

    async def history(self, turn, limit):
        earlier = [t for t in self.turns.values() if t.id < turn.id and t.status == "succeeded"]
        return [(t.question, t.answer) for t in earlier[-limit:]] if limit else []

    async def finish(self, turn_id, *, answer=None, error_code=None, model=None, latency_ms=None):
        turn = self.turns[turn_id]
        if turn.status == "pending":
            turn = replace(
                turn,
                answer=answer,
                error_code=error_code,
                status="failed" if error_code else "succeeded",
                completed_at=datetime.now(UTC),
            )
            self.turns[turn_id] = turn
        return turn


@pytest.fixture
def memory_store():
    return MemoryStore()


@pytest.fixture
async def sqlalchemy_store(context):
    app, client, _ = context
    await register(client)
    assert await conversation(client) == 1
    return SQLAlchemyChatStore(app.state.db)


@pytest.fixture(params=["memory_store", "sqlalchemy_store"])
def store(request) -> ChatStore:
    return request.getfixturevalue(request.param)


async def test_store_contract_preserves_identity_admission_and_terminal_winner(store):
    admissions = []
    key = str(uuid4())
    first = await store.reserve(1, 1, "question", key, lambda: admissions.append(1))
    assert first.created and first.turn.status == "pending"
    duplicate = await store.reserve(1, 1, "changed", key, lambda: admissions.append(2))
    assert not duplicate.created and duplicate.turn.question == "question"
    assert duplicate.turn.id == first.turn.id and admissions == [1]
    with pytest.raises(AppError) as exc:
        await store.reserve(1, 1, "another", str(uuid4()), lambda: None)
    assert exc.value.code == "CHAT_IN_PROGRESS"
    failed = await store.finish(first.turn.id, error_code="REQUEST_INTERRUPTED")
    late = await store.finish(first.turn.id, answer="late answer")
    assert late == failed and late.answer is None
    with pytest.raises(AppError) as exc:
        await store.reserve(2, 1, "question", key, lambda: None)
    assert exc.value.code == "CONVERSATION_NOT_FOUND"


async def test_service_contract_replays_and_excludes_failed_history(store):
    policy = SimpleNamespace(chat_context_turns=5, ai_timeout_seconds=1, ai_model="fake")
    ai = FakeAI()
    admitted = []
    service = ChatService(store, ai, policy, admitted.append)
    key = str(uuid4())
    first = await service.send(1, 1, "first", key)
    assert await service.send(1, 1, "first", key) == first
    assert len(ai.calls) == 1 and admitted == [1]
    with pytest.raises(AppError) as exc:
        await service.send(1, 1, "changed", key)
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    ai.error = AppError("AI_TIMEOUT")
    failed_key = str(uuid4())
    for _ in range(2):
        with pytest.raises(AppError) as exc:
            await service.send(1, 1, "failed", failed_key)
        assert exc.value.code == "AI_TIMEOUT"
    ai.error = None
    await service.send(1, 1, "next", str(uuid4()))
    assert ai.calls[-1][0] == [("first", "답변: first")]
    assert len(ai.calls) == 3


async def test_service_accepts_provider_without_lifecycle_and_translates_storage_failure():
    # The use case requires generate only; resource ownership stays in main.py.
    class Generator:
        async def generate(self, history, question):
            return "answer"

    store = MemoryStore()
    policy = SimpleNamespace(chat_context_turns=0, ai_timeout_seconds=1, ai_model="fake")
    service = ChatService(store, Generator(), policy, lambda _: None)
    result = await service.send(1, 1, "first", str(uuid4()))
    assert result.answer == "answer"

    async def broken(*args, **kwargs):
        raise StorageError()

    store.finish = broken
    with pytest.raises(AppError) as exc:
        await service.send(1, 1, "next", str(uuid4()))
    assert exc.value.code == "DB_UNAVAILABLE"
