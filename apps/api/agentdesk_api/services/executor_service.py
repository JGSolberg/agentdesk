from __future__ import annotations

import os
import subprocess

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..agent_models import AgentRun, RunStatus
from ..agent_schemas import AgentRunLogAppend, AgentRunUpdate
from ..models import TicketStatus, Workspace, WorkspaceStatus
from ..schemas import TicketUpdate
from . import agent_service, integration_service, review_service, ticket_service
from .agent_adapters import get_adapter


def execute_local_run(db: Session, run_id: str) -> AgentRun:
    run = agent_service.require_run(db, run_id)
    agent = agent_service.require_agent(db, run.agent_id)

    if run.status not in {RunStatus.QUEUED, RunStatus.NEEDS_HUMAN}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued or needs-human runs can be executed")
    if not run.workspace_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A workspace is required to execute an agent")

    workspace = db.get(Workspace, run.workspace_id)
    if not workspace or workspace.status != WorkspaceStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run workspace is not active")

    adapter = get_adapter(agent.provider)
    if not adapter:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"No executor adapter is registered for provider '{agent.provider}'")

    ticket = ticket_service.require_ticket(db, run.ticket_id)
    if ticket.status in {
        TicketStatus.BACKLOG,
        TicketStatus.READY,
        TicketStatus.REVIEW,
        TicketStatus.NEEDS_HUMAN,
        TicketStatus.AGENT_FAILED,
    }:
        ticket_service.update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.IN_PROGRESS))

    agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.RUNNING, error=None))

    try:
        default_branch = integration_service.refresh_default_branch(db, workspace)
        agent_service.append_log(
            db,
            run.id,
            AgentRunLogAppend(level="git", message=f"Fetched latest origin/{default_branch} before agent execution"),
        )
    except HTTPException as exc:
        agent_service.append_log(
            db,
            run.id,
            AgentRunLogAppend(level="warning", message=f"Unable to refresh the default branch before execution: {exc.detail}"),
        )

    try:
        plan = adapter.build_plan(agent, run, workspace)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    agent_service.append_log(db, run.id, AgentRunLogAppend(level="info", message=f"Executing {agent.name} ({agent.provider}) in {workspace.path}"))

    env = os.environ.copy()
    env.update(plan.environment)

    try:
        completed = subprocess.run(
            plan.command,
            cwd=workspace.path,
            env=env,
            shell=plan.shell,
            input=plan.stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
    except subprocess.TimeoutExpired as exc:
        message = "Agent execution timed out after 30 minutes"
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="error", message=message))
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout
        return agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.FAILED, error=message, result=stdout or None))
    except FileNotFoundError:
        executable = plan.command[0] if isinstance(plan.command, list) and plan.command else str(plan.command)
        message = f"Agent executable not found: {executable}"
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="error", message=message))
        return agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.FAILED, error=message))
    except OSError as exc:
        message = f"Unable to start agent: {exc}"
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="error", message=message))
        return agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.FAILED, error=message))

    outcome = adapter.parse_output(completed.stdout or "", completed.stderr or "", completed.returncode)
    for level, message in outcome.logs:
        if message:
            agent_service.append_log(db, run.id, AgentRunLogAppend(level=level[:30], message=message))

    unresolved_conflicts = integration_service.has_unmerged_conflicts(workspace)
    if unresolved_conflicts:
        message = "Agent finished with unresolved Git merge conflicts. Resolve them before this ticket can return to Review."
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="needs_human", message=message))
        final_status = RunStatus.NEEDS_HUMAN
        ticket_service.update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.NEEDS_HUMAN))
        return agent_service.update_run(db, run.id, AgentRunUpdate(status=final_status, result=outcome.result, error=message))

    if outcome.needs_human:
        final_status = RunStatus.NEEDS_HUMAN
        ticket_service.update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.NEEDS_HUMAN))
    else:
        final_status = RunStatus.SUCCEEDED if outcome.error is None and completed.returncode == 0 else RunStatus.FAILED
        if final_status == RunStatus.SUCCEEDED and review_service.has_reviewable_changes(db, workspace.id):
            ticket_service.update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.REVIEW))
        elif final_status == RunStatus.FAILED:
            ticket_service.update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.AGENT_FAILED))

    return agent_service.update_run(db, run.id, AgentRunUpdate(status=final_status, result=outcome.result, error=outcome.error))
