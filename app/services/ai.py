from openai import APIError, APITimeoutError, AsyncOpenAI
from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from app.errors import AppError
from app.logging import event
from app.services.prompts import build_messages


class OpenAIAdapter:
    def __init__(self, settings):
        self.model = settings.ai_model
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            max_retries=0,
            timeout=settings.ai_timeout_seconds,
        )

    async def generate(self, history, question):
        messages = build_messages(history, question)
        try:
            result = await self.client.responses.create(model=self.model, input=messages)
        except APITimeoutError:
            event("ai_provider_error", category="APITimeoutError", status_code=None)
            raise AppError("AI_TIMEOUT") from None
        except RateLimitError:
            event("ai_provider_error", category="RateLimitError", status_code=429)
            raise AppError("AI_RATE_LIMITED") from None
        except APIError as exc:
            event(
                "ai_provider_error",
                category=type(exc).__name__,
                status_code=getattr(exc, "status_code", None),
            )
            raise AppError("AI_UNAVAILABLE") from None
        answer = result.output_text.strip()
        if not answer:
            event("ai_provider_error", category="EmptyResponse", status_code=None)
            raise AppError("AI_UNAVAILABLE")
        return answer
