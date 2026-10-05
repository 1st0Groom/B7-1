from dataclasses import dataclass, field

import httpx
import pytest

from app.config import Settings
from app.main import create_app


@dataclass
class FakeAI:
    calls: list = field(default_factory=list)
    error: Exception | None = None

    async def generate(self, history, question):
        self.calls.append((history, question))
        if self.error:
            raise self.error
        return f"답변: {question}"


async def register(client, username="user_123", password="long-password-123"):
    payload = {"username": username, "password": password}
    assert (await client.post("/api/auth/signup", json=payload)).status_code == 201
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
async def context(tmp_path):
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key-never-real",
        ai_model="gpt-4o-mini",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
    )
    fake = FakeAI()
    app = create_app(settings, fake)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
        ) as client:
            yield app, client, fake
