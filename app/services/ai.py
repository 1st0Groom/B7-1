from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.errors import AppError
from app.logging import event
from app.services.prompts import build_messages


class OpenAIAdapter:
    def __init__(self, settings):
        self.model = settings.ai_model
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or "https://api.openai.com/v1",
            max_retries=0,
            timeout=settings.ai_timeout_seconds,
        )

    async def generate(self, history, question):
        messages = build_messages(history, question)
        try:
            result = await self.client.chat.completions.create(model=self.model, messages=messages)
        except APITimeoutError:
            event("ai_provider_error", category="APITimeoutError", status_code=None)
            raise AppError("AI_TIMEOUT") from None
        except RateLimitError as exc:
            event("ai_provider_error", category="RateLimitError", status_code=429)
            if exc.type == "insufficient_quota" or exc.code in {
                "insufficient_quota",
                "credit_balance_exhausted",
                "organization_spend_limit_exceeded",
                "project_spend_limit_exceeded",
                "organization_usage_limit_exceeded",
            }:
                raise AppError("AI_QUOTA_EXCEEDED") from None
            raise AppError("AI_RATE_LIMITED") from None
        except APIError as exc:
            event(
                "ai_provider_error",
                category=type(exc).__name__,
                status_code=getattr(exc, "status_code", None),
            )
            raise AppError("AI_UNAVAILABLE") from None
        content = result.choices[0].message.content if result.choices else None
        answer = (content or "").strip()
        if not answer:
            event("ai_provider_error", category="EmptyResponse", status_code=None)
            raise AppError("AI_UNAVAILABLE")
        return answer
