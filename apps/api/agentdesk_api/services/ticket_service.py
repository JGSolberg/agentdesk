from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Project, Ticket, TicketStatus, project_ticket_prefix
from ..repositories import ticket_repository
from ..schemas import TicketCreate, TicketUpdate
from .project_service import require_project


def require_ticket(db: Session, ticket_id: str) -> Ticket:
    ticket = ticket_repository.get(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _validated_parent(
    db: Session, project_id: str, parent_id: str | None, ticket_id: str | None = None
) -> Ticket | None:
    if parent_id is None:
        return None
    parent = ticket_repository.get(db, parent_id)
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


def create_ticket(db: Session, project_id: str, payload: TicketCreate) -> Ticket:
    project: Project = require_project(db, project_id)
    _validated_parent(db, project_id, payload.parent_id)
    sequence = ticket_repository.next_sequence(db, project_id)
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
    return ticket_repository.save(db, ticket)


def list_tickets(db: Session, project_id: str) -> list[Ticket]:
    require_project(db, project_id)
    return ticket_repository.list_for_project(db, project_id)


def list_ready_tickets(db: Session, project_id: str) -> list[Ticket]:
    tickets = list_tickets(db, project_id)
    return sorted((ticket for ticket in tickets if ticket.ready_to_start), key=lambda t: (t.order, t.sequence))


def update_ticket(db: Session, ticket_id: str, payload: TicketUpdate) -> Ticket:
    ticket = require_ticket(db, ticket_id)
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
    return ticket_repository.save(db, ticket)


def add_dependency(db: Session, ticket_id: str, dependency_id: str) -> Ticket:
    ticket = require_ticket(db, ticket_id)
    dependency = require_ticket(db, dependency_id)
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
    return ticket_repository.save(db, ticket)


def remove_dependency(db: Session, ticket_id: str, dependency_id: str) -> Ticket:
    ticket = require_ticket(db, ticket_id)
    dependency = require_ticket(db, dependency_id)
    if dependency not in ticket.dependencies:
        raise HTTPException(status_code=404, detail="Dependency relationship not found")
    ticket.dependencies.remove(dependency)
    _reconcile_waiting_status(ticket)
    return ticket_repository.save(db, ticket)
