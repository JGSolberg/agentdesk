from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import RepositoryProvider, TicketPriority, TicketStatus, TicketType


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


class RepositoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    local_path: str = Field(min_length=1, max_length=1000)
    provider: RepositoryProvider = RepositoryProvider.LOCAL
    remote_url: str | None = Field(default=None, max_length=1000)
    default_branch: str = Field(default="main", min_length=1, max_length=255)
    is_primary: bool = False


class RepositoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    local_path: str | None = Field(default=None, min_length=1, max_length=1000)
    provider: RepositoryProvider | None = None
    remote_url: str | None = Field(default=None, max_length=1000)
    default_branch: str | None = Field(default=None, min_length=1, max_length=255)
    is_primary: bool | None = None


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    local_path: str
    provider: RepositoryProvider
    remote_url: str | None
    default_branch: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class GitRepositoryStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path_exists: bool
    is_git_repository: bool
    branch: str | None
    head_sha: str | None
    head_message: str | None
    remote_url: str | None
    is_dirty: bool
    staged_count: int
    modified_count: int
    untracked_count: int
    error: str | None


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    type: TicketType = TicketType.STORY
    description: str | None = None
    parent_id: str | None = None
    status: TicketStatus = TicketStatus.BACKLOG
    priority: TicketPriority = TicketPriority.MEDIUM
    goal: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    definition_of_done: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    context: list[str] = Field(default_factory=list)
    estimated_complexity: str | None = Field(default=None, max_length=50)
    requires_human: bool = False
    order: float = 0.0


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    type: TicketType | None = None
    description: str | None = None
    parent_id: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    goal: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    definition_of_done: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    context: list[str] = Field(default_factory=list)
    estimated_complexity: str | None = Field(default=None, max_length=50)
    requires_human: bool = False
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
    goal: str | None
    acceptance_criteria: list[str]
    constraints: list[str]
    definition_of_done: list[str]
    relevant_files: list[str]
    context: list[str]
    estimated_complexity: str | None
    requires_human: bool
    dependency_ids: list[str]
    blocked_by_ids: list[str]
    is_blocked: bool
    ready_to_start: bool
    order: float
    created_at: datetime
    updated_at: datetime


class TicketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    event_type: str
    actor: str
    payload: dict
    created_at: datetime
