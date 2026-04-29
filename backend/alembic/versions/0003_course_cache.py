"""add course_cache table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-28 00:00:00.000000

Adds a course_cache table that stores LLM-ranked course recommendations per
career slug with a TTL (expires_at).  One row per career slug (unique index),
refreshed when expired.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("career_slug", sa.Text(), nullable=False),
        sa.Column("courses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_course_cache_career_slug",
        "course_cache",
        ["career_slug"],
        unique=True,
    )
    # Partial index for fast lookups of unexpired entries
    op.create_index(
        "ix_course_cache_expires_at",
        "course_cache",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_course_cache_expires_at", table_name="course_cache")
    op.drop_index("ix_course_cache_career_slug", table_name="course_cache")
    op.drop_table("course_cache")
