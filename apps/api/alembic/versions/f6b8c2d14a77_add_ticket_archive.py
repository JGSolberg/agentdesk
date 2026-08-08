"""add ticket archive

Revision ID: f6b8c2d14a77
Revises: e3a41b9d6c72
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f6b8c2d14a77"
down_revision: str | Sequence[str] | None = "e3a41b9d6c72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("tickets", "archived")
