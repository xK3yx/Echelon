"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # checkfirst=True queries pg_type so no error if the type already exists
    postgresql.ENUM(
        "high_school", "diploma", "bachelors", "masters", "phd",
        name="education_level",
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "low", "medium", "high",
        name="difficulty_level",
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "low", "medium", "high",
        name="growth_potential_level",
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("interests", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "education_level",
            postgresql.ENUM(
                "high_school", "diploma", "bachelors", "masters", "phd",
                name="education_level",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("personality", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "careers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("optional_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("personality_fit", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "difficulty",
            postgresql.ENUM("low", "medium", "high", name="difficulty_level", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "growth_potential",
            postgresql.ENUM(
                "low", "medium", "high", name="growth_potential_level", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("category", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_used", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("careers")
    op.drop_table("profiles")
    op.drop_table("users")

    sa.Enum(name="growth_potential_level").drop(op.get_bind())
    sa.Enum(name="difficulty_level").drop(op.get_bind())
    sa.Enum(name="education_level").drop(op.get_bind())
