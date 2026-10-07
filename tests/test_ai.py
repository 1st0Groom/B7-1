import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from openai import APIError, APITimeoutError

from app.errors import AppError
from app.services.ai import OpenAIAdapter
from app.services.prompts import SYSTEM_PROMPT


class OpenAIAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_uses_chat_completions_and_returns_trimmed_answer(self):
        settings = SimpleNamespace(
            openai_api_key="test-key",
            openai_base_url="https://copa.codyssey.kr/v1",
            ai_model="gpt-5-mini",
            ai_timeout_seconds=30,
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  답변  "))]
        )

        with patch("app.services.ai.AsyncOpenAI") as client_factory:
            client = client_factory.return_value
            client.chat.completions.create = AsyncMock(return_value=response)
            adapter = OpenAIAdapter(settings)

            answer = await adapter.generate([("이전 질문", "이전 답변")], "새 질문")

        self.assertEqual(answer, "답변")
        client_factory.assert_called_once_with(
            api_key="test-key",
            base_url="https://copa.codyssey.kr/v1",
            max_retries=0,
            timeout=30,
        )
        client.chat.completions.create.assert_awaited_once_with(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "이전 질문"},
                {"role": "assistant", "content": "이전 답변"},
                {"role": "user", "content": "새 질문"},
            ],
        )

    async def test_timeout_maps_to_ai_timeout(self):
        settings = SimpleNamespace(
            openai_api_key="test-key",
            openai_base_url="https://copa.codyssey.kr/v1",
            ai_model="gpt-5-mini",
            ai_timeout_seconds=30,
        )
        timeout = APITimeoutError(request=httpx.Request("POST", "https://example.test"))

        with patch("app.services.ai.AsyncOpenAI") as client_factory:
            client_factory.return_value.chat.completions.create = AsyncMock(side_effect=timeout)
            adapter = OpenAIAdapter(settings)

            with self.assertRaises(AppError) as raised:
                await adapter.generate([], "질문")

        self.assertEqual(raised.exception.code, "AI_TIMEOUT")

    async def test_provider_error_maps_to_unavailable_and_logs_only_error_metadata(self):
        settings = SimpleNamespace(
            openai_api_key="test-key",
            openai_base_url="https://copa.codyssey.kr/v1",
            ai_model="gpt-5-mini",
            ai_timeout_seconds=30,
        )
        provider_error = APIError(
            "provider message", httpx.Request("POST", "https://example.test"), body=None
        )

        with (
            patch("app.services.ai.AsyncOpenAI") as client_factory,
            patch("app.services.ai.event") as log_event,
        ):
            client_factory.return_value.chat.completions.create = AsyncMock(
                side_effect=provider_error
            )
            adapter = OpenAIAdapter(settings)

            with self.assertRaises(AppError) as raised:
                await adapter.generate([], "질문")

        self.assertEqual(raised.exception.code, "AI_UNAVAILABLE")
        log_event.assert_called_once_with(
            "ai_provider_error", category="APIError", status_code=None
        )

    async def test_empty_provider_answer_maps_to_unavailable(self):
        settings = SimpleNamespace(
            openai_api_key="test-key",
            openai_base_url="https://copa.codyssey.kr/v1",
            ai_model="gpt-5-mini",
            ai_timeout_seconds=30,
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  "))]
        )

        with patch("app.services.ai.AsyncOpenAI") as client_factory:
            client_factory.return_value.chat.completions.create = AsyncMock(return_value=response)
            adapter = OpenAIAdapter(settings)

            with self.assertRaises(AppError) as raised:
                await adapter.generate([], "질문")

        self.assertEqual(raised.exception.code, "AI_UNAVAILABLE")
