from fastapi import Depends, FastAPI, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Project, Ticket
from .schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    TicketCreate,
    TicketRead,
    TicketUpdate,
)
from .services import project_service, ticket_service

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


@app.post(
    "/projects/{project_id}/tickets",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(project_id: str, payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.create_ticket(db, project_id, payload)


@app.get("/projects/{project_id}/tickets", response_model=list[TicketRead])
def list_tickets(project_id: str, db: Session = Depends(get_db)) -> list[Ticket]:
    return ticket_service.list_tickets(db, project_id)


@app.get("/projects/{project_id}/tickets/ready", response_model=list[TicketRead])
def list_ready_tickets(project_id: str, db: Session = Depends(get_db)) -> list[Ticket]:
    return ticket_service.list_ready_tickets(db, project_id)


@app.get("/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.require_ticket(db, ticket_id)


@app.patch("/tickets/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket_id: str, payload: TicketUpdate, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.update_ticket(db, ticket_id, payload)


@app.post("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def add_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.add_dependency(db, ticket_id, dependency_id)


@app.delete("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def remove_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket:
    return ticket_service.remove_dependency(db, ticket_id, dependency_id)
