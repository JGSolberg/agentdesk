from fastapi import Depends, FastAPI, Query, Response, status
from sqlalchemy.orm import Session

from .agent_models import Agent, AgentRun
from .agent_schemas import AgentCreate, AgentRead, AgentRunCreate, AgentRunLogAppend, AgentRunRead, AgentRunUpdate
from .database import get_db
from .models import Project, Repository, Ticket, TicketEvent, Workspace
from .schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    RepositoryCreate,
    RepositoryRead,
    RepositoryUpdate,
    SearchResult,
    TicketCreate,
    TicketEventRead,
    TicketRead,
    TicketUpdate,
    WorkspaceAdoptWork,
    WorkspaceCreate,
    WorkspaceGitStatus,
    WorkspacePublishResult,
    WorkspaceRead,
    WorkspaceReview,
)
from .services import agent_service, executor_service, project_service, repository_service, review_service, search_service, ticket_service, workspace_service

app = FastAPI(title="AgentDesk API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]: return {"status": "ok"}

@app.get("/search", response_model=list[SearchResult])
def global_search(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=20, ge=1, le=50), db: Session = Depends(get_db)) -> list[SearchResult]: return search_service.search(db, q, limit)

@app.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project: return project_service.create_project(db, payload)
@app.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]: return project_service.list_projects(db)
@app.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project: return project_service.require_project(db, project_id)
@app.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)) -> Project: return project_service.update_project(db, project_id, payload)

@app.post("/projects/{project_id}/agents", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(project_id: str, payload: AgentCreate, db: Session = Depends(get_db)) -> Agent: return agent_service.create_agent(db, project_id, payload)
@app.get("/projects/{project_id}/agents", response_model=list[AgentRead])
def list_agents(project_id: str, db: Session = Depends(get_db)) -> list[Agent]: return agent_service.list_agents(db, project_id)

@app.post("/projects/{project_id}/repositories", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
def create_repository(project_id: str, payload: RepositoryCreate, db: Session = Depends(get_db)) -> Repository: return repository_service.create_repository(db, project_id, payload)
@app.get("/projects/{project_id}/repositories", response_model=list[RepositoryRead])
def list_repositories(project_id: str, db: Session = Depends(get_db)) -> list[Repository]: return repository_service.list_repositories(db, project_id)
@app.get("/repositories/{repository_id}", response_model=RepositoryRead)
def get_repository(repository_id: str, db: Session = Depends(get_db)) -> Repository: return repository_service.require_repository(db, repository_id)
@app.patch("/repositories/{repository_id}", response_model=RepositoryRead)
def update_repository(repository_id: str, payload: RepositoryUpdate, db: Session = Depends(get_db)) -> Repository: return repository_service.update_repository(db, repository_id, payload)
@app.post("/repositories/{repository_id}/clone", response_model=RepositoryRead)
def clone_repository(repository_id: str, db: Session = Depends(get_db)) -> Repository: return repository_service.clone_or_refresh_repository(db, repository_id)
@app.delete("/repositories/{repository_id}/clone", response_model=RepositoryRead)
def remove_repository_clone(repository_id: str, db: Session = Depends(get_db)) -> Repository: return repository_service.remove_managed_clone(db, repository_id)
@app.get("/repositories/{repository_id}/workspaces", response_model=list[WorkspaceRead])
def list_workspaces(repository_id: str, db: Session = Depends(get_db)) -> list[Workspace]: return workspace_service.list_workspaces(db, repository_id)
@app.post("/repositories/{repository_id}/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(repository_id: str, payload: WorkspaceCreate, db: Session = Depends(get_db)) -> Workspace: return workspace_service.create_workspace(db, repository_id, payload)
@app.post("/repositories/{repository_id}/workspaces/adopt", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def adopt_existing_work(repository_id: str, payload: WorkspaceAdoptWork, db: Session = Depends(get_db)) -> Workspace: return workspace_service.adopt_existing_work(db, repository_id, payload)
@app.get("/workspaces/{workspace_id}/status", response_model=WorkspaceGitStatus)
def get_workspace_status(workspace_id: str, db: Session = Depends(get_db)) -> WorkspaceGitStatus: return workspace_service.workspace_status(db, workspace_id)
@app.get("/workspaces/{workspace_id}/review", response_model=WorkspaceReview)
def get_workspace_review(workspace_id: str, db: Session = Depends(get_db)) -> WorkspaceReview: return review_service.workspace_review(db, workspace_id)
@app.post("/workspaces/{workspace_id}/publish", response_model=WorkspacePublishResult)
def publish_workspace(workspace_id: str, db: Session = Depends(get_db)) -> WorkspacePublishResult: return review_service.publish_workspace(db, workspace_id)
@app.post("/workspaces/{workspace_id}/sync-pr")
def sync_workspace_pr(workspace_id: str, db: Session = Depends(get_db)) -> dict[str, object]: return review_service.sync_pull_request(db, workspace_id)
@app.delete("/workspaces/{workspace_id}", response_model=WorkspaceRead)
def remove_workspace(workspace_id: str, db: Session = Depends(get_db)) -> Workspace: return workspace_service.remove_workspace(db, workspace_id)
@app.delete("/repositories/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(repository_id: str, db: Session = Depends(get_db)) -> Response: repository_service.delete_repository(db, repository_id); return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/projects/{project_id}/tickets", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(project_id: str, payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket: return ticket_service.create_ticket(db, project_id, payload)
@app.get("/projects/{project_id}/tickets", response_model=list[TicketRead])
def list_tickets(project_id: str, include_archived: bool = Query(default=False), db: Session = Depends(get_db)) -> list[Ticket]: return ticket_service.list_tickets(db, project_id, include_archived=include_archived)
@app.get("/projects/{project_id}/tickets/ready", response_model=list[TicketRead])
def list_ready_tickets(project_id: str, db: Session = Depends(get_db)) -> list[Ticket]: return ticket_service.list_ready_tickets(db, project_id)
@app.get("/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Ticket: return ticket_service.require_ticket(db, ticket_id)
@app.get("/tickets/{ticket_id}/events", response_model=list[TicketEventRead])
def list_ticket_events(ticket_id: str, db: Session = Depends(get_db)) -> list[TicketEvent]: return ticket_service.list_events(db, ticket_id)
@app.post("/tickets/{ticket_id}/runs", response_model=AgentRunRead, status_code=status.HTTP_201_CREATED)
def create_agent_run(ticket_id: str, payload: AgentRunCreate, db: Session = Depends(get_db)) -> AgentRun: return agent_service.create_run(db, ticket_id, payload)
@app.get("/tickets/{ticket_id}/runs", response_model=list[AgentRunRead])
def list_agent_runs(ticket_id: str, db: Session = Depends(get_db)) -> list[AgentRun]: return agent_service.list_runs(db, ticket_id)
@app.patch("/runs/{run_id}", response_model=AgentRunRead)
def update_agent_run(run_id: str, payload: AgentRunUpdate, db: Session = Depends(get_db)) -> AgentRun: return agent_service.update_run(db, run_id, payload)
@app.post("/runs/{run_id}/logs", response_model=AgentRunRead)
def append_agent_run_log(run_id: str, payload: AgentRunLogAppend, db: Session = Depends(get_db)) -> AgentRun: return agent_service.append_log(db, run_id, payload)
@app.post("/runs/{run_id}/execute", response_model=AgentRunRead)
def execute_agent_run(run_id: str, db: Session = Depends(get_db)) -> AgentRun: return executor_service.execute_local_run(db, run_id)
@app.patch("/tickets/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket_id: str, payload: TicketUpdate, db: Session = Depends(get_db)) -> Ticket: return ticket_service.update_ticket(db, ticket_id, payload)
@app.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Response: ticket_service.delete_ticket(db, ticket_id); return Response(status_code=status.HTTP_204_NO_CONTENT)
@app.post("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def add_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket: return ticket_service.add_dependency(db, ticket_id, dependency_id)
@app.delete("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def remove_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket: return ticket_service.remove_dependency(db, ticket_id, dependency_id)