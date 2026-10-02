from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    # SQLite stores naive UTC. Convert explicitly at the API boundary.
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_updated", "user_id", "updated_at", "id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(30), default="새 대화")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChatTurn(Base):
    __tablename__ = "chat_turns"
    __table_args__ = (
        Index("uq_turn_request", "conversation_id", "client_request_id", unique=True),
        Index("ix_turn_conversation_id", "conversation_id", "id"),
        Index(
            "uq_turn_pending",
            "conversation_id",
            unique=True,
            sqlite_where=text("status = 'pending'"),
        ),
        CheckConstraint("length(question) BETWEEN 1 AND 2000", name="ck_question_length"),
        CheckConstraint(
            "(status = 'pending' AND answer IS NULL AND error_code IS NULL "
            "AND completed_at IS NULL) OR "
            "(status = 'succeeded' AND answer IS NOT NULL AND length(answer) > 0 "
            "AND error_code IS NULL AND completed_at IS NOT NULL) OR "
            "(status = 'failed' AND answer IS NULL AND error_code IS NOT NULL "
            "AND completed_at IS NOT NULL)",
            name="ck_turn_state",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    client_request_id: Mapped[str] = mapped_column(String(36))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error_code: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(128))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
