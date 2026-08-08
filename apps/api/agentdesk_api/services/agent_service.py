from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent_models import Agent, AgentRun, RunStatus
from ..agent_schemas import AgentCreate, AgentRunCreate, AgentRunLogAppend, AgentRunUpdate
from ..models import TicketEvent, TicketStatus, TicketType, Workspace
from . import project_service, ticket_service


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_agent(db: Session, project_id: str, payload: AgentCreate) -> Agent:
    project_service.require_project(db, project_id)
    agent = Agent(project_id=project_id, **payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def list_agents(db: Session, project_id: str) -> list[Agent]:
    project_service.require_project(db, project_id)
    return list(db.scalars(select(Agent).where(Agent.project_id == project_id).order_by(Agent.name)))


def require_agent(db: Session, agent_id: str) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def require_run(db: Session, run_id: str) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return run


def _ticket_snapshot(ticket) -> dict:
    return {
        "ticket_key": ticket.ticket_key,
        "title": ticket.title,
        "type": ticket.type.value,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "parent_id": ticket.parent_id,
        "goal": ticket.goal,
        "description": ticket.description,
        "acceptance_criteria": ticket.acceptance_criteria,
        "definition_of_done": ticket.definition_of_done,
        "constraints": ticket.constraints,
        "context": ticket.context,
        "relevant_files": ticket.relevant_files,
        "dependency_ids": ticket.dependency_ids,
    }


def _ensure_actionable(ticket, allow_non_actionable: bool) -> None:
    reasons: list[str] = []
    if ticket.archived:
        reasons.append("archived")
    if ticket.type == TicketType.EPIC:
        reasons.append("an epic")
    if ticket.status in {TicketStatus.DONE, TicketStatus.CANCELLED}:
        reasons.append(ticket.status.value)
    if reasons and not allow_non_actionable:
        detail = ", ".join(reasons)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket is not normally actionable by an agent ({detail}). Explicitly allow a non-actionable rerun to continue.",
        )


def create_run(db: Session, ticket_id: str, payload: AgentRunCreate) -> AgentRun:
    ticket = ticket_service.require_ticket(db, ticket_id)
    _ensure_actionable(ticket, payload.allow_non_actionable)
    agent = require_agent(db, payload.agent_id)
    if agent.project_id != ticket.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent and ticket must belong to the same project")
    if not agent.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent is disabled")

    if payload.workspace_id:
        workspace = db.get(Workspace, payload.workspace_id)
        if not workspace or workspace.ticket_id != ticket.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace must belong to this ticket")

    run = AgentRun(
        ticket_id=ticket.id,
        agent_id=agent.id,
        workspace_id=payload.workspace_id,
        status=RunStatus.QUEUED,
        context_snapshot=_ticket_snapshot(ticket),
        logs=[],
    )
    db.add(run)
    db.add(TicketEvent(ticket_id=ticket.id, event_type="agent_run_created", payload={"run_id": run.id, "agent_id": agent.id, "agent_name": agent.name, "non_actionable_override": payload.allow_non_actionable}))
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, ticket_id: str) -> list[AgentRun]:
    ticket_service.require_ticket(db, ticket_id)
    return list(db.scalars(select(AgentRun).where(AgentRun.ticket_id == ticket_id).order_by(AgentRun.created_at.desc())))


def update_run(db: Session, run_id: str, payload: AgentRunUpdate) -> AgentRun:
    run = require_run(db, run_id)
    update = payload.model_dump(exclude_unset=True)
    next_status = update.get("status")
    if next_status is not None:
        if next_status == RunStatus.RUNNING and run.started_at is None:
            run.started_at = utcnow()
        if next_status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
            run.finished_at = utcnow()
    for field, value in update.items():
        setattr(run, field, value)
    db.add(TicketEvent(ticket_id=run.ticket_id, event_type="agent_run_updated", payload={"run_id": run.id, **{key: (value.value if isinstance(value, RunStatus) else value) for key, value in update.items()}}))
    db.commit()
    db.refresh(run)
    return run


def append_log(db: Session, run_id: str, payload: AgentRunLogAppend) -> AgentRun:
    run = require_run(db, run_id)
    entry = {"timestamp": utcnow().isoformat(), "level": payload.level, "message": payload.message}
    run.logs = [*run.logs, entry]
    db.commit()
    db.refresh(run)
    return run
