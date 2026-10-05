from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


class Credentials(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class QuestionInput(BaseModel):
    question: Question


class ChatOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    # SQLite returns naive UTC dates.
    created_at: Annotated[datetime, AfterValidator(lambda value: value.replace(tzinfo=UTC))]
