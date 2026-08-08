from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .bootstrap import MILESTONE_NAMES, PROJECT_NAME, ROADMAP
from .database import SessionLocal
from .models import Project, Ticket
from .schemas import TicketUpdate
from .services import ticket_service


def _project(db: Session) -> Project:
    project = db.scalar(select(Project).where(Project.name == PROJECT_NAME).order_by(Project.created_at))
    if project is None:
        raise RuntimeError("AgentDesk project not found; run the bootstrap step first")
    return project


def _roadmap_story(ticket_by_title: dict[str, Ticket], code: str, title: str) -> Ticket | None:
    # Bootstrap historically stored the roadmap code in the title. Keep accepting that
    # shape so identity repair remains idempotent without introducing a second key field.
    return ticket_by_title.get(f"{code} {title}") or ticket_by_title.get(title)


def repair_roadmap_identity(db: Session) -> int:
    project = _project(db)
    tickets = db.scalars(select(Ticket).where(Ticket.project_id == project.id)).all()
    ticket_by_title = {ticket.title: ticket for ticket in tickets}

    assignments: list[tuple[Ticket, int]] = []
    for item in ROADMAP:
        ticket = _roadmap_story(ticket_by_title, item.code, item.title)
        if ticket is None:
            raise RuntimeError(f"Canonical roadmap story missing: {item.code} {item.title}")
        assignments.append((ticket, int(item.code.split("-", 1)[1])))

    first_epic_sequence = len(ROADMAP) + 1
    for offset, (milestone, name) in enumerate(MILESTONE_NAMES.items()):
        title = f"Milestone {milestone} — {name}"
        ticket = ticket_by_title.get(title)
        if ticket is None:
            raise RuntimeError(f"Canonical milestone epic missing: {title}")
        assignments.append((ticket, first_epic_sequence + offset))

    canonical_ids = {ticket.id for ticket, _ in assignments}
    target_keys = {f"AD-{sequence}" for _, sequence in assignments}
    conflicts = [
        ticket.ticket_key
        for ticket in tickets
        if ticket.id not in canonical_ids and ticket.ticket_key in target_keys
    ]
    if conflicts:
        joined = ", ".join(sorted(conflicts))
        raise RuntimeError(f"Cannot repair roadmap keys; non-roadmap tickets already use: {joined}")

    changed = sum(
        1
        for ticket, sequence in assignments
        if ticket.sequence != sequence or ticket.ticket_key != f"AD-{sequence}"
    )
    if changed:
        # Move the canonical rows to a temporary key-space first so the per-project
        # unique constraints never collide while the existing mixed ordering is repaired.
        for offset, (ticket, _) in enumerate(assignments, start=1):
            ticket.sequence = -1000 - offset
            ticket.ticket_key = f"TMP-{ticket.id}"
        db.flush()

        for ticket, sequence in assignments:
            ticket.sequence = sequence
            ticket.ticket_key = f"AD-{sequence}"
        db.commit()

    # Refresh the repository/workspace roadmap content to match the managed-clone
    # architecture that replaced user-supplied local repository paths.
    repository_story = assignments[9][0]  # AD-10
    ticket_service.update_ticket(
        db,
        repository_story.id,
        TicketUpdate(
            goal="Register remote repositories and let AgentDesk own their local clones.",
            description=(
                "Register a repository by remote URL, keep provider/default-branch metadata, "
                "and let AgentDesk create, refresh, and remove its managed local clone."
            ),
            acceptance_criteria=[
                "Repositories are registered by remote URL rather than a user-managed local path",
                "AgentDesk derives and owns the managed clone location",
                "Managed clones can be created, refreshed, and explicitly removed",
                "Repository metadata remains associated with the AgentDesk project",
            ],
            relevant_files=[
                "apps/api/agentdesk_api/models.py",
                "apps/api/agentdesk_api/services/repository_service.py",
                "apps/web/src/RepositoryPage.tsx",
            ],
        ),
    )

    return changed


def main() -> None:
    with SessionLocal() as db:
        changed = repair_roadmap_identity(db)
        print(f"AgentDesk roadmap identity repair complete: {changed} ticket keys corrected.")


if __name__ == "__main__":
    main()
