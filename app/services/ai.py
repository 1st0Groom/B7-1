import tiktoken
from openai import APIError, APITimeoutError, AsyncOpenAI

from app.errors import AppError
from app.logging import event

SYSTEM_PROMPT = (
    "You are a helpful learning assistant. Explain concepts clearly, use examples when useful, "
    "and answer in the user's language. Be honest when uncertain."
)


class OpenAIAdapter:
    def __init__(self, settings):
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            max_retries=0,
            timeout=settings.ai_timeout_seconds,
        )
        try:
            self.encoding = (
                tiktoken.get_encoding(settings.ai_token_encoding)
                if settings.ai_token_encoding
                else tiktoken.encoding_for_model(settings.ai_model)
            )
        except (KeyError, ValueError):
            raise ValueError("Set AI_TOKEN_ENCODING for the selected AI_MODEL") from None

    def build_context(self, history, question):
        pairs = list(history)
        if self.settings.chat_context_turns:
            pairs = pairs[-self.settings.chat_context_turns :]
        else:
            pairs = []
        while sum(len(q) + len(a) for q, a in pairs) > self.settings.chat_context_max_chars:
            pairs.pop(0)
        while True:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for q, a in pairs:
                messages.extend(
                    [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
                )
            messages.append({"role": "user", "content": question})
            # Reserve framing overhead as well as model output. Count untrusted text literally.
            tokens = 64 + sum(
                16 + len(self.encoding.encode(m["content"], disallowed_special=()))
                for m in messages
            )
            if (
                tokens + self.settings.ai_max_output_tokens
                <= self.settings.ai_context_window_tokens
            ):
                return messages
            if not pairs:
                raise AppError("CONTEXT_TOO_LARGE")
            pairs.pop(0)

    async def generate(self, history, question):
        messages = self.build_context(history, question)
        try:
            result = await self.client.responses.create(
                model=self.settings.ai_model,
                input=messages,
                max_output_tokens=self.settings.ai_max_output_tokens,
                store=False,
            )
        except APITimeoutError:
            raise AppError("AI_TIMEOUT") from None
        except APIError as exc:
            event(
                "ai_provider_error",
                category=type(exc).__name__,
                status_code=getattr(exc, "status_code", None),
            )
            raise AppError("AI_UNAVAILABLE") from None
        if result.status != "completed" or not result.output_text.strip():
            raise AppError("AI_UNAVAILABLE")
        return result.output_text.strip()

    async def close(self):
        await self.client.close()
