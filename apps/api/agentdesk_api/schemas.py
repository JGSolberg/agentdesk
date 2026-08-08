from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import RepositoryProvider, TicketPriority, TicketStatus, TicketType, WorkspaceStatus


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
    provider: RepositoryProvider = RepositoryProvider.GITHUB
    remote_url: str = Field(min_length=1, max_length=1000)
    default_branch: str = Field(default="main", min_length=1, max_length=255)
    is_primary: bool = False


class RepositoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    provider: RepositoryProvider | None = None
    remote_url: str | None = Field(default=None, min_length=1, max_length=1000)
    default_branch: str | None = Field(default=None, min_length=1, max_length=255)
    is_primary: bool | None = None


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    provider: RepositoryProvider
    remote_url: str
    default_branch: str
    managed_path: str | None
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class WorkspaceCreate(BaseModel):
    ticket_id: str | None = None
    name: str | None = Field(default=None, max_length=200)
    branch: str | None = Field(default=None, max_length=255)


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    repository_id: str
    ticket_id: str | None
    name: str
    branch: str
    path: str
    status: WorkspaceStatus
    created_at: datetime
    updated_at: datetime


class WorkspaceGitStatus(BaseModel):
    branch: str
    clean: bool
    staged: int
    modified: int
    untracked: int
    ahead: int | None
    behind: int | None
    head_sha: str
    head_message: str


class WorkspaceReviewFile(BaseModel):
    path: str
    status: str


class WorkspaceReview(BaseModel):
    workspace_id: str
    branch: str
    clean: bool
    files: list[WorkspaceReviewFile]
    additions: int
    deletions: int
    diff: str
    pull_request_url: str | None = None
    pull_request_number: int | None = None


class WorkspacePublishResult(BaseModel):
    branch: str
    commit_sha: str | None
    pull_request_url: str
    pull_request_number: int | None
    created: bool


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
    archived: bool | None = None
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
    archived: bool
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


class SearchResult(BaseModel):
    kind: str
    id: str
    label: str
    subtitle: str
    href: str
    archived: bool = False
