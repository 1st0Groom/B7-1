from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    password: str = Field(min_length=10, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    client_request_id: UUID

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value):
        return value.strip() if isinstance(value, str) else value


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def as_utc(value: datetime) -> datetime:
    # SQLite returns naive UTC dates; domain records may already have a timezone.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UTCDateTime = Annotated[datetime, AfterValidator(as_utc)]


class UserOutput(BaseModel):
    id: int
    username: str


class ConversationOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


class TurnOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    client_request_id: UUID
    question: str
    answer: str | None
    status: str
    error_code: str | None
    created_at: UTCDateTime
    completed_at: UTCDateTime | None


class ConversationList(BaseModel):
    items: list[ConversationOutput]
    limit: int
    offset: int


class TurnList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[TurnOutput]
    next_before_id: int | None


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None
    turn_id: int | None


class ErrorOutput(BaseModel):
    error: ErrorDetail
