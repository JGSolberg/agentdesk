"""add ticket events

Revision ID: 9a8c4e1d2f31
Revises: c74653022d16
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "9a8c4e1d2f31"
down_revision: str | Sequence[str] | None = "c74653022d16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ticket_events_ticket_id"), "ticket_events", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_ticket_events_event_type"), "ticket_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_ticket_events_created_at"), "ticket_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ticket_events_created_at"), table_name="ticket_events")
    op.drop_index(op.f("ix_ticket_events_event_type"), table_name="ticket_events")
    op.drop_index(op.f("ix_ticket_events_ticket_id"), table_name="ticket_events")
    op.drop_table("ticket_events")
