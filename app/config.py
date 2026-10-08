from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openai_api_key: str = Field(min_length=1)
    openai_base_url: str | None = None
    ai_model: str = Field(min_length=1)
    ai_timeout_seconds: float = Field(default=30, gt=0)
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
