from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .agent_models import RunStatus


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider: str = Field(default="manual", min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=200)
    command: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    enabled: bool = True


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    provider: str
    model: str | None
    command: str | None
    capabilities: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class AgentRunCreate(BaseModel):
    agent_id: str
    workspace_id: str | None = None


class AgentRunUpdate(BaseModel):
    status: RunStatus | None = None
    result: str | None = None
    error: str | None = None


class AgentRunLogAppend(BaseModel):
    level: str = Field(default="info", max_length=30)
    message: str = Field(min_length=1)


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ticket_id: str
    agent_id: str
    workspace_id: str | None
    status: RunStatus
    context_snapshot: dict
    logs: list[dict]
    result: str | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
