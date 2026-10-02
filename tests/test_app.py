import asyncio
import hashlib
import json
import re
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import OperationalError

from app.errors import AppError
from app.logging import logger
from app.models import ChatTurn, Session, User, utcnow
from app.repositories import chat
from tests.conftest import conversation, register


def message(question="라우터란?", key=None):
    return {"question": question, "client_request_id": key or str(uuid4())}


async def test_auth_normalization_hash_cookie_and_logout(context):
    app, client, _ = context
    user = await register(client, " USER_123 ")
    assert user["username"] == "user_123"
    token = client.cookies["session"]
    async with app.state.db.sessions() as session:
        stored = await session.get(User, user["id"])
        assert stored.password_hash.startswith("$argon2id$")
        assert stored.password_hash != "long-password-123"
        saved = await session.get(Session, hashlib.sha256(token.encode()).hexdigest())
        assert saved.user_id == user["id"]
    response = await client.post(
        "/api/auth/login", json={"username": "user_123", "password": "long-password-123"}
    )
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert token != client.cookies["session"]
    response = await client.get("/api/me", headers={"Cookie": f"session={token}"})
    assert response.status_code == 401
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/me")).status_code == 401
    assert (await client.get("/chat")).status_code == 303


async def test_duplicate_login_and_expiration(context):
    app, client, _ = context
    await register(client)
    duplicate = await client.post(
        "/api/auth/signup", json={"username": "USER_123", "password": "long-password-123"}
    )
    assert duplicate.status_code == 409
    for username in ("user_123", "missing_user"):
        response = await client.post(
            "/api/auth/login", json={"username": username, "password": "wrong-password"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    async with app.state.db.sessions() as session:
        await session.execute(update(Session).values(expires_at=utcnow() - timedelta(seconds=1)))
        await session.commit()
    assert (await client.get("/api/me")).status_code == 401


async def test_origin_validation_body_limits_and_safe_errors(context):
    _, client, fake = context
    for headers in ({"Origin": "https://evil.example"}, {"Origin": "null"}, {"Origin": ""}):
        assert (await client.post("/api/auth/signup", json={}, headers=headers)).status_code == 403
    assert (
        await client.post("/api/auth/login", content="x", headers={"Content-Type": "text/plain"})
    ).status_code == 415
    assert (await client.post("/api/auth/login", content="x" * 17000)).status_code == 413
    response = await client.post("/api/auth/login", json={"password": "private-bad-password"})
    assert response.status_code == 422
    assert "private-bad-password" not in response.text
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert not fake.calls


async def test_chat_context_replay_and_ownership(context):
    app, client, fake = context
    await register(client)
    cid = await conversation(client)
    payload = message("  첫 질문  ")
    response = await client.post(f"/api/conversations/{cid}/messages", json=payload)
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["question"] == "첫 질문"
    assert first["created_at"].endswith("Z")
    assert first["completed_at"].endswith("Z")
    assert set(first) == {
        "id",
        "conversation_id",
        "client_request_id",
        "question",
        "answer",
        "status",
        "error_code",
        "created_at",
        "completed_at",
    }
    for path in (f"/api/conversations/{cid}/turns", "/api/me/chats"):
        assert (await client.get(path)).json()["items"] == [first]
    listed = (await client.get("/api/conversations")).json()["items"][0]
    assert set(listed) == {"id", "title", "created_at", "updated_at"}
    assert listed["created_at"].endswith("Z") and listed["updated_at"].endswith("Z")
    assert first["status"] == "succeeded"
    replay = await client.post(f"/api/conversations/{cid}/messages", json=payload)
    assert replay.json() == first
    assert len(fake.calls) == 1
    conflict = await client.post(
        f"/api/conversations/{cid}/messages",
        json=message("다른 질문", payload["client_request_id"]),
    )
    assert conflict.status_code == 409
    await client.post(f"/api/conversations/{cid}/messages", json=message("두 번째"))
    assert fake.calls[-1][0] == [("첫 질문", "답변: 첫 질문")]
    cid2 = await conversation(client)
    await client.post(f"/api/conversations/{cid2}/messages", json=message("별도 대화"))
    assert fake.calls[-1][0] == []
    assert len((await client.get("/api/me/chats")).json()["items"]) == 3
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8000",
        headers={"Origin": "http://localhost:8000"},
    ) as other:
        assert (
            await other.post(f"/api/conversations/{cid}/messages", json=message())
        ).status_code == 401
        await register(other, "other_user")
        assert (await other.get(f"/api/conversations/{cid}/turns")).status_code == 404
        assert (
            await other.post(f"/api/conversations/{cid}/messages", json=message())
        ).status_code == 404
        assert (await other.get("/api/me/chats")).json()["items"] == []


@pytest.mark.parametrize(
    "code,status", [("AI_TIMEOUT", 504), ("AI_UNAVAILABLE", 502), ("CONTEXT_TOO_LARGE", 422)]
)
async def test_failure_replay_manual_retry_and_context(context, code, status):
    _, client, fake = context
    await register(client)
    cid = await conversation(client)
    fake.error = AppError(code)
    payload = message()
    url = f"/api/conversations/{cid}/messages"
    for _ in range(2):
        response = await client.post(url, json=payload)
        assert response.status_code == status
        assert response.json()["error"]["turn_id"] is not None
    assert len(fake.calls) == 1
    row = (await client.get(f"/api/conversations/{cid}/turns")).json()["items"][0]
    assert row["status"] == "failed" and row["answer"] is None
    fake.error = None
    assert (await client.post(url, json=message())).status_code == 200
    assert fake.calls[-1][0] == []


async def test_timeout_concurrency_and_recovery_race(context):
    app, client, fake = context
    await register(client)
    cid = await conversation(client)
    payload = message()
    url = f"/api/conversations/{cid}/messages"
    fake.release = asyncio.Event()
    running = asyncio.create_task(client.post(url, json=payload))
    await asyncio.wait_for(fake.started.wait(), 2)
    same, different = await asyncio.gather(
        client.post(url, json=payload), client.post(url, json=message("다음 질문"))
    )
    assert same.status_code == different.status_code == 409
    assert same.json()["error"]["code"] == "CHAT_IN_PROGRESS"
    pending = (await client.get(f"/api/conversations/{cid}/turns")).json()["items"][0]
    assert pending["status"] == "pending" and pending["completed_at"] is None
    assert pending["created_at"].endswith("Z")
    # Recovery wins while a late provider result is still in flight.
    await app.state.recovery.recover_pending(all_pending=True)
    fake.release.set()
    result = await running
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "REQUEST_INTERRUPTED"
    row = (await client.get(f"/api/conversations/{cid}/turns")).json()["items"][0]
    assert row["status"] == "failed" and row["answer"] is None
    app.state.settings.ai_timeout_seconds = 0.02
    fake.release = asyncio.Event()
    assert (await client.post(url, json=message())).status_code == 504


async def test_request_cancellation_recovers(context):
    app, client, fake = context
    await register(client)
    cid = await conversation(client)
    fake.release = asyncio.Event()
    running = asyncio.create_task(client.post(f"/api/conversations/{cid}/messages", json=message()))
    await asyncio.wait_for(fake.started.wait(), 2)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    row = (await client.get(f"/api/conversations/{cid}/turns")).json()["items"][0]
    assert row["error_code"] == "REQUEST_INTERRUPTED"


@pytest.mark.parametrize("phase", ["question", "result"])
async def test_db_write_failure_never_returns_success(context, monkeypatch, phase):
    app, client, fake = context
    await register(client)
    cid = await conversation(client)
    original = chat.commit

    async def broken(session, **kwargs):
        if kwargs["phase"] == phase:
            await session.rollback()
            raise OperationalError("redacted", {}, Exception("db down"))
        await original(session, **kwargs)

    monkeypatch.setattr(chat, "commit", broken)
    response = await client.post(f"/api/conversations/{cid}/messages", json=message())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DB_UNAVAILABLE"
    assert len(fake.calls) == (0 if phase == "question" else 1)
    async with app.state.db.sessions() as session:
        rows = (await session.scalars(select(ChatTurn))).all()
        if phase == "question":
            assert not rows
        else:
            assert rows[0].status == "pending"


async def test_validation_pagination_and_rate_limit(context):
    app, client, fake = context
    await register(client)
    cid = await conversation(client)
    url = f"/api/conversations/{cid}/messages"
    for payload in (
        message("   "),
        message("x" * 2001),
        message(key="not-a-uuid"),
        message() | {"user_id": 999},
    ):
        assert (await client.post(url, json=payload)).status_code == 422
    assert not fake.calls
    for i in range(10):
        assert (await client.post(url, json=message(str(i)))).status_code == 200
    response = await client.post(url, json=message("eleven"))
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
    first = (await client.get(f"/api/conversations/{cid}/turns?limit=3")).json()
    assert [t["question"] for t in first["items"]] == ["7", "8", "9"]
    second = (
        await client.get(
            f"/api/conversations/{cid}/turns?limit=3&before_id={first['next_before_id']}"
        )
    ).json()
    assert [t["question"] for t in second["items"]] == ["4", "5", "6"]
    assert (await client.get("/api/me/chats?limit=101")).status_code == 422
    async with app.state.db.sessions() as session:
        assert await session.scalar(select(func.count(ChatTurn.id))) == 10


async def test_pages_health_and_no_secrets_in_logs(context, caplog, monkeypatch):
    _, client, _ = context
    monkeypatch.setattr(logger, "propagate", True)
    assert (await client.get("/health/live")).status_code == 200
    assert (await client.get("/health/ready")).status_code == 200
    assert (await client.get("/chat")).status_code == 303
    login = await client.get("/login")
    assert "배움" in login.text
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', login.text)
    assert len(assets) >= 2
    for asset in assets:
        response = await client.get(asset)
        assert response.status_code == 200
        assert "text/html" not in response.headers["content-type"]
    assert (await client.get("/api/not-a-route")).status_code == 404
    await register(client)
    page = await client.get("/chat")
    assert page.status_code == 200 and 'id="root"' in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    cid = await conversation(client)
    response = await client.post(
        f"/api/conversations/{cid}/messages", json=message("private-question-never-log")
    )
    assert response.status_code == 200
    entries = [json.loads(record.message) for record in caplog.records if record.name == "b7"]
    request_id = response.headers["X-Request-ID"]
    events = {entry["event"] for entry in entries if entry["request_id"] == request_id}
    assert events >= {
        "request_received",
        "ai_call_start",
        "ai_call_success",
        "db_save_success",
        "request_completed",
    }
    logs = caplog.text
    assert "private-question-never-log" not in logs
    assert "long-password-123" not in logs and "test-key-never-real" not in logs
    assert client.cookies["session"] not in logs


@pytest.mark.parametrize("username", ["ab", "a" * 33, "has space", "한글아이디", "new@example.com"])
async def test_signup_rejects_invalid_username(context, username):
    _, client, _ = context
    response = await client.post(
        "/api/auth/signup", json={"username": username, "password": "long-password-123"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("length,status", [(9, 422), (10, 201), (128, 201), (129, 422)])
async def test_password_length_without_complexity_requirement(context, length, status):
    _, client, _ = context
    payload = {"username": "new_user", "password": "a" * length}
    assert (await client.post("/api/auth/signup", json=payload)).status_code == status
    if status == 201:
        assert (await client.post("/api/auth/login", json=payload)).status_code == 200


async def test_password_spaces_are_preserved(context):
    from app.services.auth import hasher

    app, client, _ = context
    password = " password-with-spaces "
    async with app.state.db.sessions() as session:
        session.add(User(username="space_user", password_hash=hasher.hash(password)))
        await session.commit()
    payload = {"username": " SPACE_USER ", "password": password}
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    assert response.json()["username"] == "space_user"
    payload["password"] = password.strip()
    assert (await client.post("/api/auth/login", json=payload)).status_code == 401


async def test_unbuilt_frontend_keeps_api_available(context, tmp_path, monkeypatch):
    from app.routers import pages

    _, client, _ = context
    monkeypatch.setattr(pages, "FRONTEND_DIST", tmp_path)
    response = await client.get("/login")
    assert response.status_code == 503
    assert "pnpm --dir frontend build" in response.text
    assert (await client.get("/health/ready")).status_code == 200
