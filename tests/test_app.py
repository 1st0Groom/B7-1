import json

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.errors import AppError
from app.logging import logger
from app.models import Chat
from tests.conftest import register


def ask(client, question="라우터란?"):
    return client.post("/api/chat", json={"question": question})


async def test_signup_login_logout(context):
    _, client, _ = context
    await register(client)
    assert (await client.get("/api/me/chats")).status_code == 200
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/me/chats")).status_code == 401


async def test_duplicate_signup_and_wrong_password(context):
    _, client, _ = context
    await register(client)
    duplicate = await client.post(
        "/api/auth/signup", json={"username": "user_123", "password": "other"}
    )
    assert duplicate.status_code == 409
    for username in ("user_123", "missing_user"):
        response = await client.post(
            "/api/auth/login", json={"username": username, "password": "wrong-password"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_chat_requires_login(context):
    _, client, fake = context
    assert (await ask(client)).status_code == 401
    assert (await client.get("/api/me/chats")).status_code == 401
    assert not fake.calls


async def test_chat_saves_log_and_uses_recent_context(context):
    _, client, fake = context
    await register(client)
    response = await ask(client, "  첫 질문  ")
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["question"] == "첫 질문" and first["answer"] == "답변: 첫 질문"
    assert first["created_at"].endswith("Z")
    assert fake.calls[-1][0] == []
    for i in range(6):
        assert (await ask(client, str(i))).status_code == 200
    # The last five exchanges, oldest first.
    assert [q for q, _ in fake.calls[-1][0]] == ["0", "1", "2", "3", "4"]
    chats = (await client.get("/api/me/chats")).json()
    assert [chat["question"] for chat in chats] == ["첫 질문", *map(str, range(6))]


async def test_users_only_see_their_own_chats(context):
    app, client, fake = context
    await register(client)
    await ask(client, "내 질문")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
    ) as other:
        await register(other, "other_user")
        assert (await other.get("/api/me/chats")).json() == []
        await ask(other, "다른 사용자")
        assert fake.calls[-1][0] == []


@pytest.mark.parametrize("code,status", [("AI_TIMEOUT", 504), ("AI_UNAVAILABLE", 502)])
async def test_ai_failure_returns_error_and_service_keeps_working(context, code, status):
    _, client, fake = context
    await register(client)
    fake.error = AppError(code)
    response = await ask(client)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert (await client.get("/api/me/chats")).json() == []
    fake.error = None
    assert (await ask(client)).status_code == 200


async def test_unexpected_error_returns_internal_error(context):
    _, client, fake = context
    await register(client)
    fake.error = RuntimeError("private details")
    response = await ask(client)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private details" not in response.text


async def test_db_save_failure_never_returns_success(context, monkeypatch):
    app, client, _ = context
    await register(client)

    async def broken(session):
        raise OperationalError("private-db-details", {}, Exception("db down"))

    monkeypatch.setattr("sqlalchemy.ext.asyncio.AsyncSession.commit", broken)
    response = await ask(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DB_UNAVAILABLE"
    assert "private-db-details" not in response.text
    monkeypatch.undo()
    async with app.state.db.sessions() as session:
        assert not list(await session.scalars(select(Chat)))


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
async def test_question_validation(context, question):
    _, client, fake = context
    await register(client)
    response = await ask(client, question)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert not fake.calls


async def test_required_log_events(context, caplog, monkeypatch):
    _, client, _ = context
    monkeypatch.setattr(logger, "propagate", True)
    await register(client)
    caplog.clear()
    assert (await ask(client, "private-question-never-log")).status_code == 200
    entries = [json.loads(record.message) for record in caplog.records if record.name == "b7"]
    assert len({entry["request_id"] for entry in entries}) == 1
    assert list(dict.fromkeys(entry["event"] for entry in entries)) == [
        "request_received",
        "ai_call_start",
        "ai_call_success",
        "db_save_success",
    ]
    assert "private-question-never-log" not in caplog.text
    assert "long-password-123" not in caplog.text


async def test_frontend_is_served(context):
    _, client, _ = context
    page = await client.get("/")
    assert page.status_code == 200 and 'id="root"' in page.text
