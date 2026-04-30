"""add chat_messages table for the Vantage chatbot

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-30 00:00:00.000000

Stores per-recommendation conversation history with the Vantage AI
career assistant. Messages may carry an attachment (PDF, DOCX, or
image); only a short excerpt is persisted, not the binary file itself.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", name="chat_role"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachment_kind", sa.Text(), nullable=True),
        sa.Column("attachment_name", sa.Text(), nullable=True),
        sa.Column("attachment_excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendations.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_chat_messages_rec_created",
        "chat_messages",
        ["recommendation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_rec_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.execute("DROP TYPE IF EXISTS chat_role")
