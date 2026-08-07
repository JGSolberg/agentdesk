from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Project, Ticket, TicketStatus, project_ticket_prefix
from .schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    TicketCreate,
    TicketRead,
    TicketUpdate,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AgentDesk API", version="0.1.0", lifespan=lifespan)


def _require_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_ticket(db: Session, ticket_id: str) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _validated_parent(
    db: Session, project_id: str, parent_id: str | None, ticket_id: str | None = None
) -> Ticket | None:
    if parent_id is None:
        return None
    parent = db.get(Ticket, parent_id)
    if parent is None:
        raise HTTPException(status_code=400, detail="Parent ticket not found")
    if parent.project_id != project_id:
        raise HTTPException(status_code=400, detail="Parent ticket must belong to the same project")

    cursor = parent
    while ticket_id is not None and cursor is not None:
        if cursor.id == ticket_id:
            raise HTTPException(status_code=400, detail="Ticket hierarchy cannot contain a cycle")
        cursor = cursor.parent
    return parent


def _depends_on(start: Ticket, target_id: str, visited: set[str] | None = None) -> bool:
    visited = visited or set()
    if start.id in visited:
        return False
    visited.add(start.id)
    for dependency in start.dependencies:
        if dependency.id == target_id or _depends_on(dependency, target_id, visited):
            return True
    return False


def _reconcile_waiting_status(ticket: Ticket) -> None:
    """Keep waiting tickets aligned with dependency completion without rewinding active work."""
    waiting_statuses = {TicketStatus.BACKLOG, TicketStatus.READY, TicketStatus.BLOCKED}
    if ticket.status not in waiting_statuses:
        return
    if ticket.dependencies:
        ticket.status = TicketStatus.BLOCKED if ticket.is_blocked else TicketStatus.READY
    elif ticket.status == TicketStatus.BLOCKED:
        ticket.status = TicketStatus.READY


def _reconcile_dependents(ticket: Ticket) -> None:
    for dependent in ticket.dependents:
        _reconcile_waiting_status(dependent)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at)).all())


@app.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    return _require_project(db, project_id)


@app.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)) -> Project:
    project = _require_project(db, project_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.post(
    "/projects/{project_id}/tickets",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(project_id: str, payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    project = _require_project(db, project_id)
    _validated_parent(db, project_id, payload.parent_id)

    last_sequence = db.scalar(select(func.max(Ticket.sequence)).where(Ticket.project_id == project_id)) or 0
    sequence = last_sequence + 1
    ticket = Ticket(
        project_id=project_id,
        parent_id=payload.parent_id,
        sequence=sequence,
        ticket_key=f"{project_ticket_prefix(project.name)}-{sequence}",
        type=payload.type,
        status=payload.status,
        priority=payload.priority,
        title=payload.title,
        description=payload.description,
        goal=payload.goal,
        acceptance_criteria=payload.acceptance_criteria,
        constraints=payload.constraints,
        definition_of_done=payload.definition_of_done,
        relevant_files=payload.relevant_files,
        context=payload.context,
        estimated_complexity=payload.estimated_complexity,
        requires_human=payload.requires_human,
        order=payload.order,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/projects/{project_id}/tickets", response_model=list[TicketRead])
def list_tickets(project_id: str, db: Session = Depends(get_db)) -> list[Ticket]:
    _require_project(db, project_id)
    query = select(Ticket).where(Ticket.project_id == project_id).order_by(Ticket.order, Ticket.sequence)
    return list(db.scalars(query).all())


@app.get("/projects/{project_id}/tickets/ready", response_model=list[TicketRead])
def list_ready_tickets(project_id: str, db: Session = Depends(get_db)) -> list[Ticket]:
    _require_project(db, project_id)
    tickets = list(db.scalars(select(Ticket).where(Ticket.project_id == project_id)).all())
    return sorted((ticket for ticket in tickets if ticket.ready_to_start), key=lambda t: (t.order, t.sequence))


@app.get("/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Ticket:
    return _require_ticket(db, ticket_id)


@app.patch("/tickets/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket_id: str, payload: TicketUpdate, db: Session = Depends(get_db)) -> Ticket:
    ticket = _require_ticket(db, ticket_id)
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        _validated_parent(db, ticket.project_id, changes["parent_id"], ticket.id)
    if changes.get("status") == TicketStatus.READY and ticket.is_blocked:
        raise HTTPException(status_code=409, detail="Ticket cannot be Ready while dependencies are incomplete")

    status_changed = "status" in changes and changes["status"] != ticket.status
    for field, value in changes.items():
        setattr(ticket, field, value)

    if status_changed:
        _reconcile_dependents(ticket)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def add_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket:
    ticket = _require_ticket(db, ticket_id)
    dependency = _require_ticket(db, dependency_id)
    if ticket.id == dependency.id:
        raise HTTPException(status_code=400, detail="A ticket cannot depend on itself")
    if ticket.project_id != dependency.project_id:
        raise HTTPException(status_code=400, detail="Dependencies must belong to the same project")
    if dependency in ticket.dependencies:
        return ticket
    if _depends_on(dependency, ticket.id):
        raise HTTPException(status_code=400, detail="Ticket dependency graph cannot contain a cycle")

    ticket.dependencies.append(dependency)
    _reconcile_waiting_status(ticket)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.delete("/tickets/{ticket_id}/dependencies/{dependency_id}", response_model=TicketRead)
def remove_dependency(ticket_id: str, dependency_id: str, db: Session = Depends(get_db)) -> Ticket:
    ticket = _require_ticket(db, ticket_id)
    dependency = _require_ticket(db, dependency_id)
    if dependency not in ticket.dependencies:
        raise HTTPException(status_code=404, detail="Dependency relationship not found")

    ticket.dependencies.remove(dependency)
    _reconcile_waiting_status(ticket)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
