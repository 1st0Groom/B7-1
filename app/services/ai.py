from openai import APIError, APITimeoutError, AsyncOpenAI

from app.errors import AppError
from app.logging import event

SYSTEM_PROMPT = (
    "You are a helpful learning assistant. Explain concepts clearly, use examples when useful, "
    "and answer in the user's language. Be honest when uncertain."
)


class ChatCompletionsAdapter:
    def __init__(self, settings):
        self.model = settings.ai_model
        self.client = AsyncOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            max_retries=0,
            timeout=settings.ai_timeout_seconds,
        )

    async def generate(self, history, question):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for q, a in history:
            messages.extend([{"role": "user", "content": q}, {"role": "assistant", "content": a}])
        messages.append({"role": "user", "content": question})
        try:
            result = await self.client.chat.completions.create(model=self.model, messages=messages)
        except APITimeoutError:
            raise AppError("AI_TIMEOUT") from None
        except APIError as exc:
            event(
                "ai_provider_error",
                category=type(exc).__name__,
                status_code=getattr(exc, "status_code", None),
            )
            raise AppError("AI_UNAVAILABLE") from None
        answer = (result.choices[0].message.content or "").strip()
        if not answer:
            raise AppError("AI_UNAVAILABLE")
        return answer
