from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import TicketPriority, TicketStatus, TicketType


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    archived: bool | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    archived: bool
    created_at: datetime
    updated_at: datetime


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    type: TicketType = TicketType.STORY
    description: str | None = None
    parent_id: str | None = None
    status: TicketStatus = TicketStatus.BACKLOG
    priority: TicketPriority = TicketPriority.MEDIUM
    order: float = 0.0


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    type: TicketType | None = None
    description: str | None = None
    parent_id: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    order: float | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    parent_id: str | None
    sequence: int
    ticket_key: str
    type: TicketType
    status: TicketStatus
    priority: TicketPriority
    title: str
    description: str | None
    order: float
    created_at: datetime
    updated_at: datetime
