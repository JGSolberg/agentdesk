"""add workspaces

Revision ID: e3a41b9d6c72
Revises: d2f90a8c4b21
Create Date: 2026-08-07 21:12:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3a41b9d6c72"
down_revision: Union[str, Sequence[str], None] = "d2f90a8c4b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path", name="uq_workspace_path"),
        sa.UniqueConstraint("repository_id", "branch", name="uq_workspace_repository_branch"),
    )
    op.create_index(op.f("ix_workspaces_project_id"), "workspaces", ["project_id"], unique=False)
    op.create_index(op.f("ix_workspaces_repository_id"), "workspaces", ["repository_id"], unique=False)
    op.create_index(op.f("ix_workspaces_ticket_id"), "workspaces", ["ticket_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workspaces_ticket_id"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_repository_id"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_project_id"), table_name="workspaces")
    op.drop_table("workspaces")
