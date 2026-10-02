"""Create users sessions conversations and chat turns"""

import sqlalchemy as sa
from alembic import op

revision = "aba8fff08d09"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.create_index(
            "ix_conversations_user_updated", ["user_id", "updated_at", "id"], unique=False
        )

    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sessions_expires_at"), ["expires_at"], unique=False)

    op.create_table(
        "chat_turns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("client_request_id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "(status = 'pending' AND answer IS NULL AND error_code IS NULL "
            "AND completed_at IS NULL) OR "
            "(status = 'succeeded' AND answer IS NOT NULL AND length(answer) > 0 "
            "AND error_code IS NULL AND completed_at IS NOT NULL) OR "
            "(status = 'failed' AND answer IS NULL AND error_code IS NOT NULL "
            "AND completed_at IS NOT NULL)",
            name="ck_turn_state",
        ),
        sa.CheckConstraint("length(question) BETWEEN 1 AND 2000", name="ck_question_length"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("chat_turns", schema=None) as batch_op:
        batch_op.create_index("ix_turn_conversation_id", ["conversation_id", "id"], unique=False)
        batch_op.create_index(
            "uq_turn_pending",
            ["conversation_id"],
            unique=True,
            sqlite_where=sa.text("status = 'pending'"),
        )
        batch_op.create_index(
            "uq_turn_request", ["conversation_id", "client_request_id"], unique=True
        )


def downgrade():
    with op.batch_alter_table("chat_turns", schema=None) as batch_op:
        batch_op.drop_index("uq_turn_request")
        batch_op.drop_index("uq_turn_pending", sqlite_where=sa.text("status = 'pending'"))
        batch_op.drop_index("ix_turn_conversation_id")

    op.drop_table("chat_turns")
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sessions_expires_at"))

    op.drop_table("sessions")
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_index("ix_conversations_user_updated")

    op.drop_table("conversations")
    op.drop_table("users")
