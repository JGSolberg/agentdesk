from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Project, Ticket, TicketPriority, TicketStatus, TicketType
from .schemas import ProjectCreate, TicketCreate, TicketUpdate
from .services import project_service, ticket_service

PROJECT_NAME = "AgentDesk"
PROJECT_DESCRIPTION = "Local-first project management and agent orchestration for software development."

COMMON_DOD = (
    "Required automated tests pass",
    "Frontend build passes when applicable",
    "The capability is usable or discoverable from AgentDesk",
)


@dataclass(frozen=True)
class RoadmapItem:
    code: str
    title: str
    milestone: int
    goal: str
    description: str
    acceptance_criteria: tuple[str, ...]
    relevant_files: tuple[str, ...]
    complexity: str
    status: TicketStatus = TicketStatus.BACKLOG
    priority: TicketPriority = TicketPriority.MEDIUM
    constraints: tuple[str, ...] = (
        "Keep AgentDesk local-first",
        "Preserve existing API behavior unless the story explicitly changes it",
    )
    context: tuple[str, ...] = ()


ROADMAP: tuple[RoadmapItem, ...] = (
    RoadmapItem("AD-1", "Project persistence", 1, "Persist projects locally.", "Create the first durable project model and CRUD API so all later work can be scoped to a project.", ("Projects survive API restarts", "Projects can be created, listed, read, and updated", "Project IDs are stable UUIDs"), ("apps/api/agentdesk_api/models.py", "apps/api/agentdesk_api/main.py"), "small", TicketStatus.DONE),
    RoadmapItem("AD-2", "Ticket persistence", 1, "Persist project work items with stable human-readable keys.", "Add ticket storage, project-scoped sequencing, hierarchy, status, type, and priority.", ("Tickets are created within a project", "Ticket keys increment independently per project", "Tickets support parent-child hierarchy", "Ticket CRUD is covered by tests"), ("apps/api/agentdesk_api/models.py", "apps/api/agentdesk_api/services/ticket_service.py"), "medium", TicketStatus.DONE),
    RoadmapItem("AD-3", "Structured ticket fields", 1, "Store enough structured planning context for humans and future agents.", "Expand tickets beyond title/status with goal, acceptance criteria, constraints, definition of done, relevant files, context, complexity, and human-attention metadata.", ("Structured fields round-trip through the API", "List fields default safely to empty lists", "Ticket detail can consume the fields without parsing prose"), ("apps/api/agentdesk_api/models.py", "apps/api/agentdesk_api/schemas.py"), "small", TicketStatus.DONE),
    RoadmapItem("AD-4", "Dependencies", 1, "Model prerequisite work and derive whether a ticket is ready.", "Add directed ticket dependencies with cycle prevention and automatic blocked/ready reconciliation.", ("Dependencies must remain within a project", "Self and cyclic dependencies are rejected", "Incomplete dependencies block waiting tickets", "Completing dependencies makes waiting work ready"), ("apps/api/agentdesk_api/models.py", "apps/api/agentdesk_api/services/ticket_service.py"), "medium", TicketStatus.DONE),
    RoadmapItem("AD-5", "Application shell", 2, "Provide a usable web entry point for AgentDesk.", "Create the React/Vite application shell, project navigation, project overview, typed API client, and local development proxy.", ("Web app builds with TypeScript", "Projects load from FastAPI", "Project routes are navigable", "The shell works on Windows local development"), ("apps/web/src/App.tsx", "apps/web/src/api/projects.ts", "apps/web/vite.config.ts"), "medium", TicketStatus.DONE),
    RoadmapItem("AD-6", "Kanban board", 2, "Manage ticket flow visually from the project workspace.", "Render project tickets in workflow columns with creation, drag/drop status transitions, attention states, and optimistic rollback on API errors.", ("Tickets render in the correct workflow column", "New tickets can be created from the board", "Drag/drop persists status changes", "Rejected moves roll back in the UI"), ("apps/web/src/App.tsx", "apps/web/src/api/tickets.ts", "apps/web/src/board.css"), "medium", TicketStatus.DONE),
    RoadmapItem("AD-7", "Ticket detail and editing", 2, "Make a ticket the complete human-readable unit of work.", "Provide a dedicated ticket page that displays and edits structured planning fields while preserving board navigation and activity history.", ("Clicking a board card opens its ticket", "All planning fields are visible", "Core planning fields can be edited and saved", "Saved changes appear in ticket activity"), ("apps/web/src/TicketDetail.tsx", "apps/web/src/ticket-detail.css", "apps/web/src/api/tickets.ts"), "medium", TicketStatus.IN_PROGRESS, TicketPriority.HIGH),
    RoadmapItem("AD-8", "Event model", 3, "Keep an append-only audit trail of meaningful ticket actions.", "Persist ticket events for creation, updates, status movement, and dependency changes so later integrations and agents share one activity ledger.", ("Ticket events persist in their own table", "Creation and meaningful updates emit events", "Dependency changes emit events", "Events retain actor, type, payload, and timestamp"), ("apps/api/agentdesk_api/models.py", "apps/api/agentdesk_api/services/ticket_service.py", "apps/api/alembic/versions"), "medium", TicketStatus.DONE),
    RoadmapItem("AD-9", "Activity UI", 3, "Show ticket history directly on the ticket page.", "Expose ticket events through the API and render a chronological, readable activity timeline.", ("Ticket events are queryable by ticket", "Activity renders newest-first", "Status transitions are understandable without inspecting JSON", "Tickets with no history have a clear empty state"), ("apps/api/agentdesk_api/main.py", "apps/web/src/TicketDetail.tsx"), "small", TicketStatus.DONE),
    RoadmapItem("AD-10", "Repository registration", 4, "Let AgentDesk know which local codebases belong to a project.", "Add a repository registry with local path, display name, default branch, optional remote URL, and project association, managed through the GUI.", ("Repositories can be added, listed, edited, and removed", "Local path is stored explicitly", "A repository can be associated with an AgentDesk project", "The UI shows default branch and remote URL when known"), ("apps/api/agentdesk_api/models.py", "apps/api/agentdesk_api/services/repository_service.py", "apps/web/src"), "medium", priority=TicketPriority.HIGH),
    RoadmapItem("AD-11", "Worktree manager", 4, "Create isolated Git workspaces for concurrent development work.", "Manage Git worktrees tied to tickets so multiple human or agent tasks can operate without sharing a mutable checkout.", ("A ticket can request an isolated worktree", "Worktree paths and branches are tracked", "Cleanup is explicit and safe", "Existing user work is never destroyed"), ("apps/api/agentdesk_api/services/worktree_service.py",), "large", context=("Depends on repository registration",)),
    RoadmapItem("AD-12", "Git artifacts", 4, "Attach branches, commits, pull requests, and files to ticket history.", "Model Git artifacts as ticket-linked records/events so the UI can answer what code a piece of work produced.", ("Branches and commits can be linked to tickets", "PR metadata can be represented without requiring GitHub", "Artifacts appear on ticket detail", "Artifact updates are auditable"), ("apps/api/agentdesk_api/models.py", "apps/web/src/TicketDetail.tsx"), "medium", context=("Use provider-neutral concepts where possible",)),
    RoadmapItem("AD-13", "Provider interface", 5, "Define a stable abstraction for model/agent providers.", "Create provider contracts for starting work, streaming progress, tool invocation, cancellation, and result capture without coupling AgentDesk to one vendor.", ("Provider interface is documented in code", "At least one fake provider supports deterministic tests", "Provider errors normalize into AgentDesk states", "Core orchestration code has no vendor imports"), ("apps/api/agentdesk_api/providers",), "large"),
    RoadmapItem("AD-14", "GitHub Copilot adapter", 5, "Run development work through GitHub's supported agent interfaces.", "Implement the first real provider adapter for the GitHub/Copilot agent capability available to the local developer environment.", ("Adapter satisfies the provider contract", "Authentication failures are surfaced clearly", "Runs can be started and cancelled", "Provider output is captured into AgentDesk events"), ("apps/api/agentdesk_api/providers/github_copilot.py",), "large", constraints=("Use supported GitHub authentication and APIs", "Do not depend on employer-only configuration")),
    RoadmapItem("AD-15", "Agent run model", 5, "Persist each agent execution as a first-class object.", "Track run lifecycle, provider, ticket, timestamps, status, inputs, outputs, errors, and tool/activity references.", ("Runs survive server restarts", "A ticket can have multiple runs", "Run states cover queued/running/succeeded/failed/cancelled", "Run history is visible from the ticket"), ("apps/api/agentdesk_api/models.py", "apps/api/agentdesk_api/schemas.py"), "medium"),
    RoadmapItem("AD-16", "Planning agent", 6, "Turn a high-level work request into a reviewable implementation plan.", "Create the Chief of Staff planning capability that reads project/ticket/repository context and proposes scoped child work without executing code.", ("Planner can consume a ticket and repository context", "Output is structured into proposed work items", "Planner records rationale and assumptions", "No code changes occur before approval"), ("apps/api/agentdesk_api/agents/planner.py",), "large"),
    RoadmapItem("AD-17", "Plan approval UI", 6, "Let a human inspect and approve proposed work before execution.", "Add a GUI for reviewing proposed stories/tasks, editing scope, rejecting items, and approving the resulting plan into the project backlog.", ("Proposed work is clearly distinct from committed tickets", "Items can be edited before approval", "Approve creates real tickets", "Reject leaves an audit event"), ("apps/web/src",), "medium", priority=TicketPriority.HIGH),
    RoadmapItem("AD-18", "Agent Brief generator", 6, "Produce a bounded, reproducible context package for an execution agent.", "Generate a concise brief from ticket fields, dependencies, repository metadata, relevant files, and project conventions.", ("Brief includes goal, acceptance criteria, DoD, constraints, and relevant files", "Dependency context is included without dumping the whole project", "Brief output is inspectable by a human", "The same inputs produce a stable structure"), ("apps/api/agentdesk_api/agents/brief.py",), "medium"),
    RoadmapItem("AD-19", "Developer tools", 7, "Give development runs a safe set of repository and test tools.", "Implement controlled primitives for reading/writing files, running allowed commands, inspecting Git state, and reporting results within a worktree.", ("Tools are rooted to the assigned workspace", "Commands and file changes are logged", "Destructive operations require explicit policy", "Test commands return structured results"), ("apps/api/agentdesk_api/tools",), "large"),
    RoadmapItem("AD-20", "Developer execution loop", 7, "Execute an approved ticket from brief to code and verification.", "Coordinate a developer run through implementation, tests, commits, and handoff while keeping ticket/run status synchronized.", ("Execution starts only from approved/ready work", "Progress emits events", "Tests are run before success", "Failure leaves the workspace inspectable", "Successful work records its Git artifacts"), ("apps/api/agentdesk_api/agents/developer.py",), "large"),
    RoadmapItem("AD-21", "Automated review", 8, "Evaluate completed development work against the ticket rather than only the diff.", "Implement reviewer logic that reads acceptance criteria, DoD, code changes, and test results and produces actionable findings.", ("Review references ticket criteria", "Findings distinguish blockers from suggestions", "Review output is stored with the run/ticket", "Review can pass clean work without inventing issues"), ("apps/api/agentdesk_api/agents/reviewer.py",), "large"),
    RoadmapItem("AD-22", "Review workflow", 8, "Route review findings back into development until work is acceptable or needs a human.", "Add the orchestration and UI states for review, requested changes, rework, approval, and escalation.", ("Blocking review returns work to development", "Re-review is traceable", "Approval advances the ticket", "Repeated failure can enter Needs Human"), ("apps/api/agentdesk_api/services", "apps/web/src"), "large"),
    RoadmapItem("AD-23", "Dependency scheduler", 9, "Select executable work based on readiness and priority.", "Build scheduler logic that derives ready work from status/dependencies and chooses what may start without violating project constraints.", ("Blocked work is never scheduled", "Priority and explicit ordering are respected", "Scheduler decisions are explainable", "Manual status changes remain authoritative"), ("apps/api/agentdesk_api/services/scheduler_service.py",), "medium"),
    RoadmapItem("AD-24", "Parallel execution", 9, "Run independent tickets concurrently without workspace collisions.", "Combine scheduler, worktrees, and run tracking to execute multiple ready work items with configurable concurrency.", ("Independent tickets can run concurrently", "Each run uses an isolated workspace", "Concurrency has a configurable limit", "One failed run does not corrupt another"), ("apps/api/agentdesk_api/services/scheduler_service.py", "apps/api/agentdesk_api/services/worktree_service.py"), "large"),
    RoadmapItem("AD-25", "Epic progress", 9, "Summarize child-work progress at the epic level.", "Derive epic completion, blockers, active work, and remaining work from child tickets and surface it in project views.", ("Epic progress derives from children", "Blocked child work is visible", "Completed epics are recognizable on the board", "No manually maintained percentage is required"), ("apps/api/agentdesk_api/services", "apps/web/src"), "medium"),
    RoadmapItem("AD-26", "Conversational project control", 10, "Operate AgentDesk through a natural-language project command surface.", "Add a Chief of Staff console that can answer project questions and propose safe actions using the same service layer as the GUI.", ("Console can answer what is ready/in progress/blocked", "Actions are explicit and auditable", "Destructive or high-impact actions require confirmation", "The console does not bypass service-layer rules"), ("apps/web/src", "apps/api/agentdesk_api/agents"), "large"),
    RoadmapItem("AD-27", "Human attention queue", 10, "Give the user one place to see decisions and failures that need intervention.", "Aggregate Needs Human, agent failures, approval requests, and blocked decisions into an actionable queue.", ("Attention items link back to their source ticket/run", "Resolved items leave the queue", "Queue distinguishes decision requests from failures", "Project-wide attention count is visible"), ("apps/web/src", "apps/api/agentdesk_api/services"), "medium", priority=TicketPriority.HIGH),
)

MILESTONE_NAMES = {
    1: "Ticket core", 2: "Usable project UI", 3: "Event ledger", 4: "Git workspace management",
    5: "Agent runtime foundation", 6: "Chief of Staff", 7: "Developer agent", 8: "Reviewer agent",
    9: "Scheduler and parallel work", 10: "Chief of Staff console",
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


def _ticket_payload(item: RoadmapItem, parent_id: str, order: float) -> dict:
    return {
        "title": f"{item.code} {item.title}",
        "type": TicketType.STORY,
        "parent_id": parent_id,
        "status": item.status,
        "priority": item.priority,
        "goal": item.goal,
        "description": item.description,
        "acceptance_criteria": list(item.acceptance_criteria),
        "constraints": list(item.constraints),
        "definition_of_done": list(COMMON_DOD),
        "relevant_files": list(item.relevant_files),
        "context": list(item.context),
        "estimated_complexity": item.complexity,
        "order": order,
    }


def bootstrap(db: Session) -> tuple[Project, int]:
    project = _find_project(db)
    if project is None:
        project = project_service.create_project(db, ProjectCreate(name=PROJECT_NAME, description=PROJECT_DESCRIPTION))

    existing = _existing_by_code(db, project.id)
    created = 0
    milestone_epics: dict[int, Ticket] = {}
    all_tickets = ticket_service.list_tickets(db, project.id)

    for milestone, name in MILESTONE_NAMES.items():
        epic_title = f"Milestone {milestone} — {name}"
        epic = next((ticket for ticket in all_tickets if ticket.title == epic_title), None)
        if epic is None:
            epic_status = TicketStatus.DONE if milestone <= 3 else TicketStatus.BACKLOG
            epic = ticket_service.create_ticket(db, project.id, TicketCreate(title=epic_title, type=TicketType.EPIC, status=epic_status, priority=TicketPriority.HIGH, order=float(milestone * 100)))
            created += 1
        milestone_epics[milestone] = epic

    for index, item in enumerate(ROADMAP, start=1):
        payload = _ticket_payload(item, milestone_epics[item.milestone].id, float(item.milestone * 100 + index))
        current = existing.get(item.code)
        if current is None:
            ticket_service.create_ticket(db, project.id, TicketCreate(**payload))
            created += 1
            continue

        # Synchronize canonical roadmap planning content while preserving the user's current workflow status.
        payload.pop("status")
        ticket_service.update_ticket(db, current.id, TicketUpdate(**payload))

    return project, created


def main() -> None:
    with SessionLocal() as db:
        project, created = bootstrap(db)
        total = len(ticket_service.list_tickets(db, project.id))
        print(f"AgentDesk bootstrap complete: {created} created, {total} total tickets.")


if __name__ == "__main__":
    main()
