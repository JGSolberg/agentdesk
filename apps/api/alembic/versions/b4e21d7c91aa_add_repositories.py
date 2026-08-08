"""add repositories

Revision ID: b4e21d7c91aa
Revises: 9a8c4e1d2f31
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b4e21d7c91aa"
down_revision: Union[str, Sequence[str], None] = "9a8c4e1d2f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("local_path", sa.String(length=1000), nullable=False),
        sa.Column("provider", sa.String(length=6), nullable=False),
        sa.Column("remote_url", sa.String(length=1000), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "local_path", name="uq_repository_project_path"),
    )
    op.create_index(op.f("ix_repositories_project_id"), "repositories", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_repositories_project_id"), table_name="repositories")
    op.drop_table("repositories")
