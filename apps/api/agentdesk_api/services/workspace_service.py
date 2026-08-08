from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import TicketEvent, Workspace, WorkspaceStatus
from ..repositories import event_repository, workspace_repository
from ..schemas import WorkspaceAdoptWork, WorkspaceCreate, WorkspaceGitStatus
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


def _git_output(args: list[str], *, cwd: Path, allow_failure: bool = False) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=str(cwd), check=not allow_failure, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Git executable was not found") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "Git operation failed"
        raise HTTPException(status_code=502, detail=detail) from exc
    if result.returncode != 0 and not allow_failure:
        raise HTTPException(status_code=502, detail=result.stderr.strip() or "Git operation failed")
    return result.stdout.strip()


def _git(args: list[str], *, cwd: Path) -> None:
    _git_output(args, cwd=cwd)


def _record_workspace_event(db: Session, workspace: Workspace, event_type: str, extra: dict | None = None) -> None:
    if not workspace.ticket_id:
        return
    payload = {"workspace_id": workspace.id, "repository_id": workspace.repository_id, "name": workspace.name, "branch": workspace.branch, "path": workspace.path}
    if extra:
        payload.update(extra)
    event_repository.add(db, TicketEvent(ticket_id=workspace.ticket_id, event_type=event_type, actor="user", payload=payload))


def _branch_worktree_path(managed_clone: Path, branch: str) -> Path | None:
    listing = _git_output(["worktree", "list", "--porcelain"], cwd=managed_clone)
    current_path: Path | None = None
    target_ref = f"refs/heads/{branch}"
    for line in listing.splitlines():
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree ")).resolve()
        elif line == f"branch {target_ref}" and current_path is not None:
            return current_path
        elif not line.strip():
            current_path = None
    return None


def _clear_readonly_and_retry(function, path: str, _excinfo) -> None:
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        function(path)
    except OSError:
        return


def _remove_path_long_safe(path: Path) -> bool:
    if not path.exists():
        return True
    target = str(path)
    if os.name == "nt" and not target.startswith("\\\\?\\"):
        target = f"\\\\?\\{target}"
    try:
        shutil.rmtree(target, onexc=_clear_readonly_and_retry)
    except FileNotFoundError:
        return True
    except OSError:
        pass
    if not path.exists():
        return True
    if os.name == "nt":
        subprocess.run(["cmd.exe", "/d", "/c", "attrib", "-R", f"{target}\\*", "/S", "/D"], capture_output=True, text=True, check=False)
        subprocess.run(["cmd.exe", "/d", "/c", "rmdir", "/S", "/Q", target], capture_output=True, text=True, check=False)
    return not path.exists()


def _prepare_reactivation_path(repository_id: str, managed_clone: Path, workspace: Workspace) -> Path:
    root = _workspace_root(repository_id)
    path = Path(workspace.path).resolve()
    if root not in path.parents:
        raise HTTPException(status_code=409, detail="Refusing to reactivate a workspace outside AgentDesk storage")
    existing_branch_path = _branch_worktree_path(managed_clone, workspace.branch)
    if existing_branch_path is not None and existing_branch_path != path:
        if root not in existing_branch_path.parents:
            raise HTTPException(status_code=409, detail=f"Branch {workspace.branch} is already checked out outside AgentDesk storage")
        _git_output(["worktree", "remove", "--force", str(existing_branch_path)], cwd=managed_clone, allow_failure=True)
        _remove_path_long_safe(existing_branch_path)
        _git_output(["worktree", "prune"], cwd=managed_clone, allow_failure=True)
    _git(["worktree", "prune"], cwd=managed_clone)
    return path


def workspace_status(db: Session, workspace_id: str) -> WorkspaceGitStatus:
    workspace = require_workspace(db, workspace_id)
    if workspace.status != WorkspaceStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Workspace is not active")
    path = Path(workspace.path).resolve()
    if not path.exists():
        raise HTTPException(status_code=409, detail="Workspace path is missing")
    valid = _git_output(["rev-parse", "--is-inside-work-tree"], cwd=path, allow_failure=True)
    if valid.lower() != "true":
        raise HTTPException(status_code=409, detail="Workspace cleanup is incomplete. Git worktree metadata is unavailable; use Sync & finalize to finish cleanup.")
    porcelain = _git_output(["status", "--porcelain=v1"], cwd=path)
    staged = modified = untracked = 0
    for line in porcelain.splitlines():
        if line.startswith("??"):
            untracked += 1
            continue
        if len(line) >= 2:
            if line[0] != " ": staged += 1
            if line[1] != " ": modified += 1
    branch = _git_output(["branch", "--show-current"], cwd=path) or workspace.branch
    head_sha = _git_output(["rev-parse", "--short", "HEAD"], cwd=path)
    head_message = _git_output(["log", "-1", "--pretty=%s"], cwd=path)
    ahead = behind = None
    tracking = _git_output(["rev-list", "--left-right", "--count", "@{upstream}...HEAD"], cwd=path, allow_failure=True)
    if tracking:
        parts = tracking.split()
        if len(parts) == 2:
            behind, ahead = int(parts[0]), int(parts[1])
    return WorkspaceGitStatus(branch=branch, clean=(staged + modified + untracked) == 0, staged=staged, modified=modified, untracked=untracked, ahead=ahead, behind=behind, head_sha=head_sha, head_message=head_message)


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
    managed_clone = Path(repository.managed_path).resolve()
    _git(["fetch", "--prune", "origin"], cwd=managed_clone)
    existing = workspace_repository.get_by_branch(db, repository.id, branch)
    if existing is not None:
        if existing.status == WorkspaceStatus.ACTIVE:
            if existing.ticket_id == (ticket.id if ticket else None): return existing
            raise HTTPException(status_code=409, detail=f"Branch {branch} already has an active workspace")
        path = _prepare_reactivation_path(repository.id, managed_clone, existing)
        _git(["worktree", "add", str(path), branch], cwd=managed_clone)
        existing.ticket_id = ticket.id if ticket else None
        existing.name = name
        existing.status = WorkspaceStatus.ACTIVE
        existing = workspace_repository.save(db, existing)
        _record_workspace_event(db, existing, "workspace_reactivated")
        return existing
    workspace_id = __import__("uuid").uuid4().hex
    path = (_workspace_root(repository.id) / workspace_id).resolve()
    root = _workspace_root(repository.id)
    if root not in path.parents:
        raise HTTPException(status_code=409, detail="Refusing to create a workspace outside AgentDesk storage")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _git(["worktree", "add", "-b", branch, str(path), f"origin/{repository.default_branch}"], cwd=managed_clone)
    except HTTPException as exc:
        if "already exists" not in str(exc.detail): raise
        _git(["worktree", "add", str(path), branch], cwd=managed_clone)
    workspace = Workspace(id=workspace_id, project_id=repository.project_id, repository_id=repository.id, ticket_id=ticket.id if ticket else None, name=name, branch=branch, path=str(path), status=WorkspaceStatus.ACTIVE)
    workspace = workspace_repository.save(db, workspace)
    _record_workspace_event(db, workspace, "workspace_created")
    return workspace


def _resolve_pr_branch(managed_clone: Path, pull_request: str) -> tuple[str, dict[str, object]]:
    try:
        result = subprocess.run(["gh", "pr", "view", pull_request, "--json", "number,url,headRefName,baseRefName,state,mergedAt"], cwd=str(managed_clone), capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="GitHub CLI was not found") from exc
    if result.returncode != 0:
        raise HTTPException(status_code=409, detail=result.stderr.strip() or "Unable to resolve pull request")
    try:
        pr = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="GitHub CLI returned invalid pull request metadata") from exc
    branch = str(pr.get("headRefName") or "").strip()
    if not branch:
        raise HTTPException(status_code=409, detail="Pull request has no head branch")
    return branch, pr


def adopt_existing_work(db: Session, repository_id: str, payload: WorkspaceAdoptWork) -> Workspace:
    repository = require_repository(db, repository_id)
    if not repository.managed_path:
        raise HTTPException(status_code=409, detail="Clone the repository before adopting existing work")
    ticket = require_ticket(db, payload.ticket_id)
    if ticket.project_id != repository.project_id:
        raise HTTPException(status_code=409, detail="Ticket and repository must belong to the same project")
    managed_clone = Path(repository.managed_path).resolve()

    pr: dict[str, object] | None = None
    branch = (payload.branch or "").strip()
    if payload.pull_request:
        pr_branch, pr = _resolve_pr_branch(managed_clone, payload.pull_request)
        if branch and branch != pr_branch:
            raise HTTPException(status_code=409, detail=f"Pull request head branch is {pr_branch}, not {branch}")
        branch = pr_branch
    if not branch:
        raise HTTPException(status_code=422, detail="branch or pull_request is required")

    existing = workspace_repository.get_by_branch(db, repository.id, branch)
    if existing and existing.status == WorkspaceStatus.ACTIVE:
        if existing.ticket_id == ticket.id:
            return existing
        raise HTTPException(status_code=409, detail=f"Branch {branch} already belongs to another active workspace")

    _git(["fetch", "--prune", "origin", branch], cwd=managed_clone)
    remote_branch = _git_output(["show-ref", "--verify", f"refs/remotes/origin/{branch}"], cwd=managed_clone, allow_failure=True)
    if not remote_branch:
        raise HTTPException(status_code=404, detail=f"Remote branch origin/{branch} was not found")
    local_branch = _git_output(["show-ref", "--verify", f"refs/heads/{branch}"], cwd=managed_clone, allow_failure=True)
    if not local_branch:
        _git(["branch", "--track", branch, f"origin/{branch}"], cwd=managed_clone)

    if existing:
        path = _prepare_reactivation_path(repository.id, managed_clone, existing)
        existing.ticket_id = ticket.id
        existing.name = ticket.ticket_key
        existing.status = WorkspaceStatus.ACTIVE
        workspace = existing
    else:
        workspace_id = __import__("uuid").uuid4().hex
        path = (_workspace_root(repository.id) / workspace_id).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        workspace = Workspace(id=workspace_id, project_id=repository.project_id, repository_id=repository.id, ticket_id=ticket.id, name=ticket.ticket_key, branch=branch, path=str(path), status=WorkspaceStatus.ACTIVE)

    _git(["worktree", "add", str(path), branch], cwd=managed_clone)
    workspace = workspace_repository.save(db, workspace)
    extra: dict[str, object] = {"adopted_branch": branch}
    if pr:
        extra.update({"pull_request_url": pr.get("url"), "pull_request_number": pr.get("number"), "base_branch": pr.get("baseRefName")})
    _record_workspace_event(db, workspace, "workspace_adopted", extra)
    return workspace


def remove_workspace(db: Session, workspace_id: str) -> Workspace:
    workspace = require_workspace(db, workspace_id)
    if workspace.status == WorkspaceStatus.REMOVED: return workspace
    repository = require_repository(db, workspace.repository_id)
    if not repository.managed_path:
        raise HTTPException(status_code=409, detail="Managed clone is unavailable")
    path = Path(workspace.path).resolve()
    root = _workspace_root(repository.id)
    if root not in path.parents:
        raise HTTPException(status_code=409, detail="Refusing to remove a workspace outside AgentDesk storage")
    managed_clone = Path(repository.managed_path).resolve()
    if path.exists():
        _git_output(["worktree", "remove", "--force", str(path)], cwd=managed_clone, allow_failure=True)
        _remove_path_long_safe(path)
    _git_output(["worktree", "prune"], cwd=managed_clone, allow_failure=True)
    workspace.status = WorkspaceStatus.REMOVED
    workspace = workspace_repository.save(db, workspace)
    _record_workspace_event(db, workspace, "workspace_removed")
    return workspace