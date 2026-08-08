from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Project, Ticket, TicketPriority, TicketStatus, TicketType
from .schemas import ProjectCreate, TicketCreate
from .services import project_service, ticket_service

PROJECT_NAME = "AgentDesk"
PROJECT_DESCRIPTION = "Local-first project management and agent orchestration for software development."

@dataclass(frozen=True)
class RoadmapItem:
    code: str
    title: str
    milestone: int
    status: TicketStatus = TicketStatus.BACKLOG
    priority: TicketPriority = TicketPriority.MEDIUM

ROADMAP: tuple[RoadmapItem, ...] = (
    RoadmapItem("AD-1", "Project persistence", 1, TicketStatus.DONE),
    RoadmapItem("AD-2", "Ticket persistence", 1, TicketStatus.DONE),
    RoadmapItem("AD-3", "Structured ticket fields", 1, TicketStatus.DONE),
    RoadmapItem("AD-4", "Dependencies", 1, TicketStatus.DONE),
    RoadmapItem("AD-5", "Application shell", 2, TicketStatus.DONE),
    RoadmapItem("AD-6", "Kanban board", 2, TicketStatus.DONE),
    RoadmapItem("AD-7", "Ticket detail view", 2, TicketStatus.IN_PROGRESS, TicketPriority.HIGH),
    RoadmapItem("AD-8", "Event model", 3),
    RoadmapItem("AD-9", "Activity UI", 3),
    RoadmapItem("AD-10", "Repository registration", 4),
    RoadmapItem("AD-11", "Worktree manager", 4),
    RoadmapItem("AD-12", "Git artifacts", 4),
    RoadmapItem("AD-13", "Provider interface", 5),
    RoadmapItem("AD-14", "GitHub Copilot adapter", 5),
    RoadmapItem("AD-15", "Agent run model", 5),
    RoadmapItem("AD-16", "Planning agent", 6),
    RoadmapItem("AD-17", "Plan approval UI", 6),
    RoadmapItem("AD-18", "Agent Brief generator", 6),
    RoadmapItem("AD-19", "Developer tools", 7),
    RoadmapItem("AD-20", "Developer execution loop", 7),
    RoadmapItem("AD-21", "Automated review", 8),
    RoadmapItem("AD-22", "Review workflow", 8),
    RoadmapItem("AD-23", "Dependency scheduler", 9),
    RoadmapItem("AD-24", "Parallel execution", 9),
    RoadmapItem("AD-25", "Epic progress", 9),
    RoadmapItem("AD-26", "Conversational project control", 10),
    RoadmapItem("AD-27", "Human attention queue", 10),
)

MILESTONE_NAMES = {
    1: "Ticket core",
    2: "Usable project UI",
    3: "Event ledger",
    4: "Git workspace management",
    5: "Agent runtime foundation",
    6: "Chief of Staff",
    7: "Developer agent",
    8: "Reviewer agent",
    9: "Scheduler and parallel work",
    10: "Chief of Staff console",
}

def _find_project(db: Session) -> Project | None:
    return db.scalar(select(Project).where(Project.name == PROJECT_NAME).order_by(Project.created_at))

def _existing_by_code(db: Session, project_id: str) -> dict[str, Ticket]:
    found: dict[str, Ticket] = {}
    for ticket in ticket_service.list_tickets(db, project_id):
        code = ticket.title.split(" ", 1)[0]
        if code.startswith("AD-"):
            found[code] = ticket
    return found

def bootstrap(db: Session) -> tuple[Project, int]:
    project = _find_project(db)
    if project is None:
        project = project_service.create_project(
            db, ProjectCreate(name=PROJECT_NAME, description=PROJECT_DESCRIPTION)
        )

    existing = _existing_by_code(db, project.id)
    created = 0
    milestone_epics: dict[int, Ticket] = {}
    all_tickets = ticket_service.list_tickets(db, project.id)

    for milestone, name in MILESTONE_NAMES.items():
        epic_title = f"Milestone {milestone} — {name}"
        epic = next((ticket for ticket in all_tickets if ticket.title == epic_title), None)
        if epic is None:
            epic_status = (
                TicketStatus.DONE if milestone == 1
                else TicketStatus.IN_PROGRESS if milestone == 2
                else TicketStatus.BACKLOG
            )
            epic = ticket_service.create_ticket(
                db,
                project.id,
                TicketCreate(
                    title=epic_title,
                    type=TicketType.EPIC,
                    status=epic_status,
                    priority=TicketPriority.HIGH,
                    order=float(milestone * 100),
                ),
            )
            created += 1
        milestone_epics[milestone] = epic

    for index, item in enumerate(ROADMAP, start=1):
        if item.code in existing:
            continue
        ticket_service.create_ticket(
            db,
            project.id,
            TicketCreate(
                title=f"{item.code} {item.title}",
                type=TicketType.STORY,
                parent_id=milestone_epics[item.milestone].id,
                status=item.status,
                priority=item.priority,
                goal=f"Implement {item.title.lower()} for AgentDesk.",
                definition_of_done=[
                    "Required tests pass",
                    "Frontend build passes when applicable",
                    "Behavior is documented or discoverable in AgentDesk",
                ],
                order=float(item.milestone * 100 + index),
            ),
        )
        created += 1

    return project, created

def main() -> None:
    with SessionLocal() as db:
        project, created = bootstrap(db)
        total = len(ticket_service.list_tickets(db, project.id))
        print(f"AgentDesk bootstrap complete: {created} created, {total} total tickets.")

if __name__ == "__main__":
    main()
