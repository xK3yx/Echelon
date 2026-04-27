"""careers provenance fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-27 00:00:00.000000

Adds data-provenance columns to the careers table:
  source               — where the record came from (onet / manual / llm_proposed)
  onet_soc_code        — O*NET-SOC code for source=onet rows
  external_url         — link to the authoritative source page
  verified             — false only for llm_proposed rows pending admin review
  proposed_for_profile_id — FK to the profile that triggered the LLM proposal
  updated_at           — auto-updated via trigger on every row change
  deleted_at           — soft-delete timestamp; NULL means active
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New enum for career data provenance
    postgresql.ENUM(
        "onet", "manual", "llm_proposed",
        name="career_source",
    ).create(op.get_bind(), checkfirst=True)

    # Add columns as nullable first so the backfill can run
    op.add_column(
        "careers",
        sa.Column(
            "source",
            postgresql.ENUM("onet", "manual", "llm_proposed", name="career_source", create_type=False),
            nullable=True,
        ),
    )
    op.add_column("careers", sa.Column("onet_soc_code", sa.Text(), nullable=True))
    op.add_column("careers", sa.Column("external_url", sa.Text(), nullable=True))
    op.add_column("careers", sa.Column("verified", sa.Boolean(), nullable=True))
    op.add_column(
        "careers",
        sa.Column(
            "proposed_for_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "careers",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )
    op.add_column("careers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill existing 20 manual rows
    op.execute("UPDATE careers SET source = 'manual', verified = true, updated_at = now()")

    # Enforce NOT NULL now that backfill is done
    op.alter_column("careers", "source", nullable=False)
    op.alter_column("careers", "verified", nullable=False)
    op.alter_column("careers", "updated_at", nullable=False)

    # Unique index on onet_soc_code (partial — only for non-null values, since
    # multiple manual/proposed rows will all have NULL and that's allowed)
    op.create_index(
        "ix_careers_onet_soc_code",
        "careers",
        ["onet_soc_code"],
        unique=True,
        postgresql_where=sa.text("onet_soc_code IS NOT NULL"),
    )

    # FK from proposed_for_profile_id → profiles.id
    op.create_foreign_key(
        "fk_careers_proposed_for_profile",
        "careers",
        "profiles",
        ["proposed_for_profile_id"],
        ["id"],
    )

    # Trigger function + trigger to auto-update updated_at on every row change
    op.execute("""
        CREATE OR REPLACE FUNCTION set_careers_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_careers_updated_at
        BEFORE UPDATE ON careers
        FOR EACH ROW EXECUTE FUNCTION set_careers_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_careers_updated_at ON careers")
    op.execute("DROP FUNCTION IF EXISTS set_careers_updated_at()")
    op.drop_constraint("fk_careers_proposed_for_profile", "careers", type_="foreignkey")
    op.drop_index("ix_careers_onet_soc_code", table_name="careers")
    op.drop_column("careers", "deleted_at")
    op.drop_column("careers", "updated_at")
    op.drop_column("careers", "proposed_for_profile_id")
    op.drop_column("careers", "verified")
    op.drop_column("careers", "external_url")
    op.drop_column("careers", "onet_soc_code")
    op.drop_column("careers", "source")
    sa.Enum(name="career_source").drop(op.get_bind())
