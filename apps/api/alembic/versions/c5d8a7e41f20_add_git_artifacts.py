"""add git artifacts

Revision ID: c5d8a7e41f20
Revises: a7c31f2e9b44
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d8a7e41f20"
down_revision: str | Sequence[str] | None = "a7c31f2e9b44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("git_artifacts", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ticket_id", sa.String(36), nullable=False), sa.Column("repository_id", sa.String(36), nullable=True), sa.Column("kind", sa.String(20), nullable=False), sa.Column("identifier", sa.String(1000), nullable=False), sa.Column("title", sa.String(500), nullable=True), sa.Column("url", sa.String(2000), nullable=True), sa.Column("metadata", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="SET NULL"))
    op.create_index(op.f("ix_git_artifacts_ticket_id"), "git_artifacts", ["ticket_id"])
    op.create_index(op.f("ix_git_artifacts_repository_id"), "git_artifacts", ["repository_id"])
    op.create_index(op.f("ix_git_artifacts_kind"), "git_artifacts", ["kind"])


def downgrade() -> None:
    op.drop_table("git_artifacts")
