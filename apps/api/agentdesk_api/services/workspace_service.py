from __future__ import annotations

import os
from pathlib import Path
import subprocess

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import TicketEvent, Workspace, WorkspaceStatus
from ..repositories import event_repository, workspace_repository
from ..schemas import WorkspaceCreate
from .repository_service import require_repository
from .ticket_service import require_ticket


def _agentdesk_home() -> Path:
    configured = os.getenv("AGENTDESK_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".agentdesk").resolve()


def _workspace_root(repository_id: str) -> Path:
    return (_agentdesk_home() / "workspaces" / repository_id).resolve()


def require_workspace(db: Session, workspace_id: str) -> Workspace:
    workspace = workspace_repository.get(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def list_workspaces(db: Session, repository_id: str) -> list[Workspace]:
    require_repository(db, repository_id)
    return workspace_repository.list_for_repository(db, repository_id)


def _git(args: list[str], *, cwd: Path) -> None:
    try:
        subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Git executable was not found") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "Git operation failed"
        raise HTTPException(status_code=502, detail=detail) from exc


def _record_workspace_event(db: Session, workspace: Workspace, event_type: str) -> None:
    if not workspace.ticket_id:
        return
    event_repository.add(
        db,
        TicketEvent(
            ticket_id=workspace.ticket_id,
            event_type=event_type,
            actor="user",
            payload={
                "workspace_id": workspace.id,
                "repository_id": workspace.repository_id,
                "name": workspace.name,
                "branch": workspace.branch,
                "path": workspace.path,
            },
        ),
    )


def create_workspace(db: Session, repository_id: str, payload: WorkspaceCreate) -> Workspace:
    repository = require_repository(db, repository_id)
    if not repository.managed_path:
        raise HTTPException(status_code=409, detail="Clone the repository before creating a workspace")

    ticket = None
    if payload.ticket_id:
        ticket = require_ticket(db, payload.ticket_id)
        if ticket.project_id != repository.project_id:
            raise HTTPException(status_code=409, detail="Workspace ticket must belong to the repository project")

    branch = payload.branch or (f"agent/{ticket.ticket_key}" if ticket else None)
    if not branch:
        raise HTTPException(status_code=422, detail="branch is required when no ticket is supplied")

    name = payload.name or (ticket.ticket_key if ticket else branch.replace("/", "-"))
    workspace_id = __import__("uuid").uuid4().hex
    path = (_workspace_root(repository.id) / workspace_id).resolve()
    root = _workspace_root(repository.id)
    if root not in path.parents:
        raise HTTPException(status_code=409, detail="Refusing to create a workspace outside AgentDesk storage")
    path.parent.mkdir(parents=True, exist_ok=True)

    managed_clone = Path(repository.managed_path).resolve()
    _git(["fetch", "--prune", "origin"], cwd=managed_clone)
    try:
        _git(["worktree", "add", "-b", branch, str(path), f"origin/{repository.default_branch}"], cwd=managed_clone)
    except HTTPException as exc:
        if "already exists" not in str(exc.detail):
            raise
        _git(["worktree", "add", str(path), branch], cwd=managed_clone)

    workspace = Workspace(
        id=workspace_id,
        project_id=repository.project_id,
        repository_id=repository.id,
        ticket_id=ticket.id if ticket else None,
        name=name,
        branch=branch,
        path=str(path),
        status=WorkspaceStatus.ACTIVE,
    )
    workspace = workspace_repository.save(db, workspace)
    _record_workspace_event(db, workspace, "workspace_created")
    return workspace


def remove_workspace(db: Session, workspace_id: str) -> Workspace:
    workspace = require_workspace(db, workspace_id)
    if workspace.status == WorkspaceStatus.REMOVED:
        return workspace

    repository = require_repository(db, workspace.repository_id)
    if not repository.managed_path:
        raise HTTPException(status_code=409, detail="Managed clone is unavailable")

    path = Path(workspace.path).resolve()
    root = _workspace_root(repository.id)
    if root not in path.parents:
        raise HTTPException(status_code=409, detail="Refusing to remove a workspace outside AgentDesk storage")

    managed_clone = Path(repository.managed_path).resolve()
    if path.exists():
        _git(["worktree", "remove", str(path)], cwd=managed_clone)
    _git(["worktree", "prune"], cwd=managed_clone)

    workspace.status = WorkspaceStatus.REMOVED
    workspace = workspace_repository.save(db, workspace)
    _record_workspace_event(db, workspace, "workspace_removed")
    return workspace
