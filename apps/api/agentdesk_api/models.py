from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
import re
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
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


class RepositoryProvider(StrEnum):
    GITHUB = "github"
    GITLAB = "gitlab"
    OTHER = "other"


class WorkspaceStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


def project_ticket_prefix(name: str) -> str:
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


ticket_dependencies = Table(
    "ticket_dependencies",
    Base.metadata,
    Column("ticket_id", ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
    Column("dependency_id", ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tickets: Mapped[list[Ticket]] = relationship(back_populates="project", cascade="all, delete-orphan")
    repositories: Mapped[list[Repository]] = relationship(back_populates="project", cascade="all, delete-orphan")
    workspaces: Mapped[list[Workspace]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("project_id", "remote_url", name="uq_repository_project_remote"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[RepositoryProvider] = mapped_column(
        SqlEnum(RepositoryProvider, native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        default=RepositoryProvider.GITHUB,
        nullable=False,
    )
    remote_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    managed_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    project: Mapped[Project] = relationship(back_populates="repositories")
    workspaces: Mapped[list[Workspace]] = relationship(back_populates="repository", cascade="all, delete-orphan")


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
    type: Mapped[TicketType] = mapped_column(SqlEnum(TicketType, native_enum=False, values_callable=lambda enum: [item.value for item in enum]), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(SqlEnum(TicketStatus, native_enum=False, values_callable=lambda enum: [item.value for item in enum]), default=TicketStatus.BACKLOG, nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(SqlEnum(TicketPriority, native_enum=False, values_callable=lambda enum: [item.value for item in enum]), default=TicketPriority.MEDIUM, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    constraints: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    definition_of_done: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    relevant_files: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    context: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    estimated_complexity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    project: Mapped[Project] = relationship(back_populates="tickets")
    parent: Mapped[Ticket | None] = relationship(remote_side="Ticket.id", back_populates="children")
    children: Mapped[list[Ticket]] = relationship(back_populates="parent")
    events: Mapped[list[TicketEvent]] = relationship(back_populates="ticket", cascade="all, delete-orphan", order_by="TicketEvent.created_at")
    workspaces: Mapped[list[Workspace]] = relationship(back_populates="ticket")
    dependencies: Mapped[list[Ticket]] = relationship(secondary=ticket_dependencies, primaryjoin=id == ticket_dependencies.c.ticket_id, secondaryjoin=id == ticket_dependencies.c.dependency_id, back_populates="dependents")
    dependents: Mapped[list[Ticket]] = relationship(secondary=ticket_dependencies, primaryjoin=id == ticket_dependencies.c.dependency_id, secondaryjoin=id == ticket_dependencies.c.ticket_id, back_populates="dependencies")

    @property
    def dependency_ids(self) -> list[str]:
        return [ticket.id for ticket in self.dependencies]

    @property
    def blocked_by_ids(self) -> list[str]:
        return [ticket.id for ticket in self.dependencies if ticket.status != TicketStatus.DONE]

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocked_by_ids)

    @property
    def ready_to_start(self) -> bool:
        return not self.is_blocked and self.status in {TicketStatus.BACKLOG, TicketStatus.BLOCKED, TicketStatus.READY}


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("repository_id", "branch", name="uq_workspace_repository_branch"),
        UniqueConstraint("path", name="uq_workspace_path"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False)
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[WorkspaceStatus] = mapped_column(
        SqlEnum(WorkspaceStatus, native_enum=False, values_callable=lambda enum: [item.value for item in enum]),
        default=WorkspaceStatus.ACTIVE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    project: Mapped[Project] = relationship(back_populates="workspaces")
    repository: Mapped[Repository] = relationship(back_populates="workspaces")
    ticket: Mapped[Ticket | None] = relationship(back_populates="workspaces")


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(120), default="user", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    ticket: Mapped[Ticket] = relationship(back_populates="events")
