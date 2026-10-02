import asyncio
from dataclasses import dataclass, field

import httpx
import pytest
from alembic import command
from alembic.config import Config

from app.config import Settings
from app.main import create_app


@dataclass
class FakeAI:
    calls: list = field(default_factory=list)
    error: Exception | None = None
    started: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event | None = None

    async def generate(self, history, question):
        self.calls.append((history, question))
        self.started.set()
        if self.release:
            await self.release.wait()
        if self.error:
            raise self.error
        return f"답변: {question}"

    async def close(self):
        pass


def migrate(url, target="head"):
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    command.upgrade(config, target)


@pytest.fixture
async def context(tmp_path):
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key-never-real",
        ai_model="gpt-4o-mini",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
    )
    await asyncio.to_thread(migrate, settings.database_url)
    fake = FakeAI()
    app = create_app(settings, fake)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost:8000",
            headers={"Origin": settings.app_origin},
        ) as client:
            yield app, client, fake


async def register(client, username="user_123"):
    payload = {"username": username, "password": "long-password-123"}
    response = await client.post("/api/auth/signup", json=payload)
    assert response.status_code == 201, response.text
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


async def conversation(client):
    response = await client.post("/api/conversations", json={})
    assert response.status_code == 201, response.text
    return response.json()["id"]
