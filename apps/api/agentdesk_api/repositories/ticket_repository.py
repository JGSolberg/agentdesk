from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Ticket


def get(db: Session, ticket_id: str) -> Ticket | None:
    return db.get(Ticket, ticket_id)


def list_for_project(db: Session, project_id: str, *, include_archived: bool = False) -> list[Ticket]:
    query = select(Ticket).where(Ticket.project_id == project_id)
    if not include_archived:
        query = query.where(Ticket.archived.is_(False))
    return list(db.scalars(query.order_by(Ticket.order, Ticket.sequence)).all())


def next_sequence(db: Session, project_id: str) -> int:
    last_sequence = db.scalar(select(func.max(Ticket.sequence)).where(Ticket.project_id == project_id)) or 0
    return last_sequence + 1


def save(db: Session, ticket: Ticket) -> Ticket:
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def delete(db: Session, ticket: Ticket) -> None:
    db.delete(ticket)
    db.commit()
