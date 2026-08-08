from fastapi import Depends, FastAPI, Query, Response, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Project, Repository, Ticket, TicketEvent, Workspace
from .schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    RepositoryCreate,
    RepositoryRead,
    RepositoryUpdate,
    TicketCreate,
    TicketEventRead,
    TicketRead,
    TicketUpdate,
    WorkspaceCreate,
    WorkspaceGitStatus,
    WorkspaceRead,
)
from .services import project_service, repository_service, ticket_service, workspace_service

app = FastAPI(title="AgentDesk API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    return project_service.create_project(db, payload)


@app.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return project_service.list_projects(db)


@app.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    return project_service.require_project(db, project_id)


@app.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)) -> Project:
    return project_service.update_project(db, project_id, payload)


@app.post("/projects/{project_id}/repositories", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
def create_repository(project_id: str, payload: RepositoryCreate, db: Session = Depends(get_db)) -> Repository:
    return repository_service.create_repository(db, project_id, payload)


@app.get("/projects/{project_id}/repositories", response_model=list[RepositoryRead])
def list_repositories(project_id: str, db: Session = Depends(get_db)) -> list[Repository]:
    return repository_service.list_repositories(db, project_id)


@app.get("/repositories/{repository_id}", response_model=RepositoryRead)
def get_repository(repository_id: str, db: Session = Depends(get_db)) -> Repository:
    return repository_service.require_repository(db, repository_id)


@app.patch("/repositories/{repository_id}", response_model=RepositoryRead)
def update_repository(repository_id: str, payload: RepositoryUpdate, db: Session = Depends(get_db)) -> Repository:
    return repository_service.update_repository(db, repository_id, payload)


@app.post("/repositories/{repository_id}/clone", response_model=RepositoryRead)
def clone_repository(repository_id: str, db: Session = Depends(get_db)) -> Repository:
    return repository_service.clone_or_refresh_repository(db, repository_id)


@app.delete("/repositories/{repository_id}/clone", response_model=RepositoryRead)
def remove_repository_clone(repository_id: str, db: Session = Depends(get_db)) -> Repository:
    return repository_service.remove_managed_clone(db, repository_id)


@app.get("/repositories/{repository_id}/workspaces", response_model=list[WorkspaceRead])
def list_workspaces(repository_id: str, db: Session = Depends(get_db)) -> list[Workspace]:
    return workspace_service.list_workspaces(db, repository_id)


@app.post("/repositories/{repository_id}/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(repository_id: str, payload: WorkspaceCreate, db: Session = Depends(get_db)) -> Workspace:
    return workspace_service.create_workspace(db, repository_id, payload)


@app.get("/workspaces/{workspace_id}/status", response_model=WorkspaceGitStatus)
def get_workspace_status(workspace_id: str, db: Session = Depends(get_db)) -> WorkspaceGitStatus:
    return workspace_service.workspace_status(db, workspace_id)


@app.delete("/workspaces/{workspace_id}", response_model=WorkspaceRead)
def remove_workspace(workspace_id: str, db: Session = Depends(get_db)) -> Workspace:
    return workspace_service.remove_workspace(db, workspace_id)


@app.delete("/repositories/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(repository_id: str, db: Session = Depends(get_db)) -> Response:
    repository_service.delete_repository(db, repository_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/projects/{project_id}/tickets", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(project_id: str, payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.create_ticket(db, project_id, payload)


@app.get("/projects/{project_id}/tickets", response_model=list[TicketRead])
def list_tickets(
    project_id: str,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[Ticket]:
    return ticket_service.list_tickets(db, project_id, include_archived=include_archived)


@app.get("/projects/{project_id}/tickets/ready", response_model=list[TicketRead])
def list_ready_tickets(project_id: str, db: Session = Depends(get_db)) -> list[Ticket]:
    return ticket_service.list_ready_tickets(db, project_id)


@app.get("/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.require_ticket(db, ticket_id)


@app.get("/tickets/{ticket_id}/events", response_model=list[TicketEventRead])
def list_ticket_events(ticket_id: str, db: Session = Depends(get_db)) -> list[TicketEvent]:
    return ticket_service.list_events(db, ticket_id)


@app.patch("/tickets/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket_id: str, payload: TicketUpdate, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.update_ticket(db, ticket_id, payload)


@app.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Response:
    ticket_service.delete_ticket(db, ticket_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def add_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.add_dependency(db, ticket_id, dependency_id)


@app.delete("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def remove_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.remove_dependency(db, ticket_id, dependency_id)
