import sqlite3
from datetime import timedelta
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.main import create_app
from app.models import ChatTurn, Conversation, User, utcnow
from tests.conftest import FakeAI


def test_migration_round_trip_and_constraints(tmp_path):
    path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.attributes["database_url"] = f"sqlite+aiosqlite:///{path}"
    command.upgrade(config, "head")
    command.check(config)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert {row[1] for row in db.execute("PRAGMA index_list(chat_turns)")} >= {
            "uq_turn_pending",
            "uq_turn_request",
        }
    command.downgrade(config, "base")
    command.upgrade(config, "head")


async def test_restart_recovers_pending_and_keeps_data(context):
    app, _, _ = context
    async with app.state.db.sessions() as session:
        user = User(username="restart_user", password_hash="irrelevant")
        session.add(user)
        await session.flush()
        conversation = Conversation(user_id=user.id)
        session.add(conversation)
        await session.flush()
        turn = ChatTurn(
            conversation_id=conversation.id,
            question="interrupted",
            client_request_id=str(uuid4()),
            created_at=utcnow() - timedelta(seconds=1),
        )
        session.add(turn)
        await session.commit()
        turn_id = turn.id
    second = create_app(app.state.settings, FakeAI())
    async with second.router.lifespan_context(second):
        async with second.state.db.sessions() as session:
            turn = await session.get(ChatTurn, turn_id)
            assert turn.status == "failed" and turn.error_code == "REQUEST_INTERRUPTED"
            assert await session.scalar(select(User.username)) == "restart_user"
