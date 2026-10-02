from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


def timestamp(value: datetime | None):
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z") if value else None


def turn_json(turn):
    return {
        name: getattr(turn, name)
        for name in (
            "id",
            "conversation_id",
            "client_request_id",
            "question",
            "answer",
            "status",
            "error_code",
        )
    } | {"created_at": timestamp(turn.created_at), "completed_at": timestamp(turn.completed_at)}


def conversation_json(conversation):
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": timestamp(conversation.created_at),
        "updated_at": timestamp(conversation.updated_at),
    }


class UserOutput(BaseModel):
    id: int
    username: str


class ConversationOutput(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class TurnOutput(BaseModel):
    id: int
    conversation_id: int
    client_request_id: UUID
    question: str
    answer: str | None
    status: str
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None


class ConversationList(BaseModel):
    items: list[ConversationOutput]
    limit: int
    offset: int


class TurnList(BaseModel):
    items: list[TurnOutput]
    next_before_id: int | None


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None
    turn_id: int | None


class ErrorOutput(BaseModel):
    error: ErrorDetail
