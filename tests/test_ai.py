import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.ai import SYSTEM_PROMPT, ChatCompletionsAdapter


class ChatCompletionsAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_uses_chat_completions_and_returns_trimmed_answer(self):
        settings = SimpleNamespace(
            ai_api_key="test-key",
            ai_base_url="https://copa.codyssey.kr/v1",
            ai_model="gpt-5-mini",
            ai_timeout_seconds=30,
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  답변  "))]
        )

        with patch("app.services.ai.AsyncOpenAI") as client_factory:
            client = client_factory.return_value
            client.chat.completions.create = AsyncMock(return_value=response)
            adapter = ChatCompletionsAdapter(settings)

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
