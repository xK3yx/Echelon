"""add is_public to recommendations

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-29 00:00:00.000000

Adds is_public boolean to recommendations.  When True the result is
accessible via the public /api/recommendations/{id}/public endpoint and
the /r/{id} share page without any authentication.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "is_public")
