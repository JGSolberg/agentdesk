from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
import re
import uuid

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TicketType(StrEnum):
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    BUG = "bug"
    SPIKE = "spike"


class TicketStatus(StrEnum):
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"
    AGENT_FAILED = "agent_failed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def project_ticket_prefix(name: str) -> str:
    """Create a compact, deterministic ticket prefix from a project name."""
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+", name)
    if len(words) >= 2:
        prefix = "".join(word[0] for word in words[:3])
    elif words:
        word = words[0]
        capitals = "".join(char for char in name if char.isupper())
        prefix = capitals[:3] if len(capitals) >= 2 else word[:2]
    else:
        prefix = "AD"
    cleaned = re.sub(r"[^A-Za-z0-9]", "", prefix).upper()
    return (cleaned or "AD")[:5]


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    tickets: Mapped[list[Ticket]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("project_id", "sequence", name="uq_ticket_project_sequence"),
        UniqueConstraint("project_id", "ticket_key", name="uq_ticket_project_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    ticket_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    type: Mapped[TicketType] = mapped_column(
        SqlEnum(TicketType, native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SqlEnum(TicketStatus, native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        default=TicketStatus.BACKLOG,
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SqlEnum(TicketPriority, native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="tickets")
    parent: Mapped[Ticket | None] = relationship(remote_side="Ticket.id", back_populates="children")
    children: Mapped[list[Ticket]] = relationship(back_populates="parent")
