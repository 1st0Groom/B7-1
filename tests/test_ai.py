import json
from contextlib import asynccontextmanager

import httpx
import pytest
from openai import AsyncOpenAI

from app.config import Settings
from app.errors import AppError
from app.services.ai import OpenAIAdapter


def settings(**kwargs):
    return Settings(_env_file=None, openai_api_key="fake-only", ai_model="gpt-4o-mini", **kwargs)


@asynccontextmanager
async def mocked_adapter(handler):
    adapter = OpenAIAdapter(settings())
    await adapter.client.close()
    adapter.client = AsyncOpenAI(
        api_key="fake-only",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        yield adapter
    finally:
        await adapter.close()


async def test_real_sdk_serialization_and_no_retries():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "gpt-4o-mini",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": "테스트 답변", "annotations": []}
                        ],
                    }
                ],
            },
        )

    async with mocked_adapter(handler) as adapter:
        assert await adapter.generate([("이전", "답변")], "현재") == "테스트 답변"
        assert calls[0]["store"] is False
        assert calls[0]["max_output_tokens"] == 1000
        assert [m["role"] for m in calls[0]["input"]] == ["system", "user", "assistant", "user"]


@pytest.mark.parametrize("status", [401, 429, 500])
async def test_provider_errors_are_sanitized(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "secret-provider-payload"}})

    async with mocked_adapter(handler) as adapter:
        with pytest.raises(AppError) as exc:
            await adapter.generate([], "질문")
        assert exc.value.code == "AI_UNAVAILABLE"
        assert len(calls) == 1
        assert "secret" not in str(exc.value)


async def test_context_bounds_and_literal_special_tokens():
    adapter = OpenAIAdapter(settings(chat_context_max_chars=8))
    try:
        context = adapter.build_context([("old", "long answer"), ("new", "yes")], "<|endoftext|>")
        assert [m["content"] for m in context[1:]] == ["new", "yes", "<|endoftext|>"]
        adapter.settings.ai_context_window_tokens = 1100
        with pytest.raises(AppError) as exc:
            adapter.build_context([], "긴 질문" * 2000)
        assert exc.value.code == "CONTEXT_TOO_LARGE"
    finally:
        await adapter.close()


async def test_sdk_network_timeout_is_translated_without_retry():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("private-provider-details", request=request)

    async with mocked_adapter(handler) as adapter:
        with pytest.raises(AppError) as exc:
            await adapter.generate([], "질문")
        assert exc.value.code == "AI_TIMEOUT"
        assert len(calls) == 1
        assert "private-provider-details" not in str(exc.value)
