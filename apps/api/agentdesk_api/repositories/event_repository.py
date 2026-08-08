from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TicketEvent


def add(db: Session, event: TicketEvent) -> TicketEvent:
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_for_ticket(db: Session, ticket_id: str) -> list[TicketEvent]:
    query = select(TicketEvent).where(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.created_at)
    return list(db.scalars(query).all())
