from __future__ import annotations

import json
import os
import subprocess

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..agent_models import AgentRun, RunStatus
from ..agent_schemas import AgentRunLogAppend, AgentRunUpdate
from ..models import Workspace, WorkspaceStatus
from . import agent_service


def execute_local_run(db: Session, run_id: str) -> AgentRun:
    run = agent_service.require_run(db, run_id)
    agent = agent_service.require_agent(db, run.agent_id)

    if run.status not in {RunStatus.QUEUED, RunStatus.NEEDS_HUMAN}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued or needs-human runs can be executed")
    if not agent.command:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent has no command configured")
    if agent.provider not in {"local", "command"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This executor only supports local command agents")
    if not run.workspace_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A workspace is required to execute a local agent")

    workspace = db.get(Workspace, run.workspace_id)
    if not workspace or workspace.status != WorkspaceStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run workspace is not active")

    agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.RUNNING, error=None))
    agent_service.append_log(db, run.id, AgentRunLogAppend(level="info", message=f"Executing {agent.name} in {workspace.path}"))

    env = os.environ.copy()
    env.update({
        "AGENTDESK_RUN_ID": run.id,
        "AGENTDESK_TICKET_ID": run.ticket_id,
        "AGENTDESK_TICKET_KEY": str(run.context_snapshot.get("ticket_key", "")),
        "AGENTDESK_WORKSPACE": workspace.path,
        "AGENTDESK_TICKET_CONTEXT_JSON": json.dumps(run.context_snapshot),
    })

    try:
        completed = subprocess.run(agent.command, cwd=workspace.path, env=env, shell=True, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired as exc:
        message = "Agent command timed out after 30 minutes"
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="error", message=message))
        return agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.FAILED, error=message, result=exc.stdout or None))
    except OSError as exc:
        message = f"Unable to start agent command: {exc}"
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="error", message=message))
        return agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.FAILED, error=message))

    if completed.stdout:
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="stdout", message=completed.stdout.rstrip()))
    if completed.stderr:
        agent_service.append_log(db, run.id, AgentRunLogAppend(level="stderr", message=completed.stderr.rstrip()))

    if completed.returncode == 0:
        return agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.SUCCEEDED, result=completed.stdout.rstrip() or "Command completed successfully", error=None))

    message = f"Agent command exited with code {completed.returncode}"
    return agent_service.update_run(db, run.id, AgentRunUpdate(status=RunStatus.FAILED, result=completed.stdout.rstrip() or None, error=message))
