from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .bootstrap import COMMON_DOD, MILESTONE_NAMES, PROJECT_NAME, ROADMAP
from .database import SessionLocal
from .models import Project, Ticket, TicketType
from .schemas import TicketUpdate
from .services import ticket_service


def enrich_roadmap_epics(db: Session) -> int:
    project = db.scalar(select(Project).where(Project.name == PROJECT_NAME).order_by(Project.created_at))
    if project is None:
        return 0

    tickets = ticket_service.list_tickets(db, project.id, include_archived=True)
    updated = 0

    for milestone, name in MILESTONE_NAMES.items():
        epic_title = f"Milestone {milestone} — {name}"
        epic = next((ticket for ticket in tickets if ticket.type == TicketType.EPIC and ticket.title == epic_title), None)
        if epic is None:
            continue

        children = [item for item in ROADMAP if item.milestone == milestone]
        child_labels = [f"{item.code} {item.title}" for item in children]
        relevant_files = list(dict.fromkeys(path for item in children for path in item.relevant_files))
        constraints = list(dict.fromkeys(constraint for item in children for constraint in item.constraints))

        payload = TicketUpdate(
            goal=f"Deliver the {name} milestone as a coherent, usable slice of AgentDesk.",
            description=(
                f"This epic groups the roadmap work for milestone {milestone}: "
                + ", ".join(child_labels)
                + ". Progress is derived from these child stories rather than maintained manually."
            ),
            acceptance_criteria=[f"{label} is complete or explicitly cancelled" for label in child_labels],
            constraints=constraints,
            definition_of_done=[*COMMON_DOD, "All child stories are complete or explicitly cancelled"],
            relevant_files=relevant_files,
            context=[f"Roadmap child: {label}" for label in child_labels],
            estimated_complexity="epic",
        )
        before = (
            epic.goal,
            epic.description,
            epic.acceptance_criteria,
            epic.constraints,
            epic.definition_of_done,
            epic.relevant_files,
            epic.context,
            epic.estimated_complexity,
        )
        ticket_service.update_ticket(db, epic.id, payload)
        after = (
            epic.goal,
            epic.description,
            epic.acceptance_criteria,
            epic.constraints,
            epic.definition_of_done,
            epic.relevant_files,
            epic.context,
            epic.estimated_complexity,
        )
        if before != after:
            updated += 1

    return updated


def main() -> None:
    with SessionLocal() as db:
        updated = enrich_roadmap_epics(db)
        print(f"AgentDesk roadmap epic enrichment complete: {updated} epics updated.")


if __name__ == "__main__":
    main()
