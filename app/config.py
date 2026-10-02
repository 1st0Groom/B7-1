from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    app_env: Literal["development", "production"] = "development"
    app_origin: str = "http://localhost:8000"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    openai_api_key: SecretStr
    ai_model: str = Field(min_length=1)
    ai_timeout_seconds: float = Field(default=30, gt=0, le=30)
    ai_max_output_tokens: int = Field(default=1000, ge=16, le=1000)
    ai_context_window_tokens: int = Field(default=8192, ge=1024)
    ai_token_encoding: str = ""
    chat_context_turns: int = Field(default=5, ge=0, le=5)
    chat_context_max_chars: int = Field(default=12000, ge=0, le=12000)
    session_ttl_seconds: int = Field(default=86400, ge=60, le=86400)
    cookie_secure: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def validate_environment(self):
        origin = urlsplit(self.app_origin)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.path
            or origin.query
            or origin.fragment
            or origin.username
        ):
            raise ValueError("APP_ORIGIN must be an HTTP(S) origin without a trailing slash")
        if not self.openai_api_key.get_secret_value().strip() or not self.ai_model.strip():
            raise ValueError("OPENAI_API_KEY and AI_MODEL must be configured")
        if not self.database_url.startswith("sqlite+aiosqlite:///"):
            raise ValueError("This deployment supports SQLite with aiosqlite only")
        if self.app_env == "production" and (origin.scheme != "https" or not self.cookie_secure):
            raise ValueError("Production requires HTTPS APP_ORIGIN and COOKIE_SECURE=true")
        if self.ai_context_window_tokens <= self.ai_max_output_tokens + 256:
            raise ValueError("AI_CONTEXT_WINDOW_TOKENS must leave room for input")
        return self
