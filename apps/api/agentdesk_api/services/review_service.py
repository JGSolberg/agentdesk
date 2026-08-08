from __future__ import annotations

import difflib
import json
from pathlib import Path
import subprocess

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import TicketEvent, TicketStatus, Workspace, WorkspaceStatus
from ..repositories import event_repository
from ..schemas import TicketUpdate, WorkspacePublishResult, WorkspaceReview, WorkspaceReviewFile
from .repository_service import require_repository
from .ticket_service import require_ticket, update_ticket
from .workspace_service import remove_workspace, require_workspace


_EXCLUDE_PATHSPEC = ":(exclude).agentdesk/**"


def _run(args: list[str], *, cwd: Path, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Executable was not found: {args[0]}") from exc
    if result.returncode != 0 and not allow_failure:
        raise HTTPException(status_code=502, detail=result.stderr.strip() or result.stdout.strip() or f"{args[0]} failed")
    return result


def _workspace_path(workspace: Workspace) -> Path:
    if workspace.status != WorkspaceStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Workspace is not active")
    path = Path(workspace.path).resolve()
    if not path.exists():
        raise HTTPException(status_code=409, detail="Workspace path is missing")
    return path


def _existing_pr(path: Path, branch: str) -> dict[str, object] | None:
    try:
        result = _run(["gh", "pr", "view", branch, "--json", "url,number,state,mergedAt"], cwd=path, allow_failure=True)
    except HTTPException as exc:
        if exc.status_code == 503:
            return None
        raise
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    url = str(payload.get("url") or "").strip()
    if not url:
        return None
    return {
        "url": url,
        "number": payload.get("number") if isinstance(payload.get("number"), int) else None,
        "state": str(payload.get("state") or "").lower(),
        "merged": bool(payload.get("mergedAt")),
    }


def _status_lines(path: Path) -> list[str]:
    result = _run(["git", "status", "--porcelain=v1", "--untracked-files=all", "--", ".", _EXCLUDE_PATHSPEC], cwd=path)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _review_files(path: Path) -> list[WorkspaceReviewFile]:
    files: list[WorkspaceReviewFile] = []
    for line in _status_lines(path):
        code = line[:2]
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1]
        files.append(WorkspaceReviewFile(path=raw_path, status=code))
    return files


def _untracked_diff(path: Path, files: list[WorkspaceReviewFile]) -> str:
    chunks: list[str] = []
    for item in files:
        if item.status != "??":
            continue
        file_path = path / item.path
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            chunks.append(f"diff --git a/{item.path} b/{item.path}\nnew file (binary or unreadable)\n")
            continue
        chunks.append(
            "".join(
                difflib.unified_diff(
                    [],
                    text.splitlines(keepends=True),
                    fromfile=f"a/{item.path}",
                    tofile=f"b/{item.path}",
                    lineterm="\n",
                )
            )
        )
    return "\n".join(chunk for chunk in chunks if chunk)


def workspace_review(db: Session, workspace_id: str) -> WorkspaceReview:
    workspace = require_workspace(db, workspace_id)
    path = _workspace_path(workspace)
    files = _review_files(path)
    tracked = _run(["git", "diff", "HEAD", "--", ".", _EXCLUDE_PATHSPEC], cwd=path).stdout
    diff = tracked
    untracked = _untracked_diff(path, files)
    if untracked:
        diff = f"{diff.rstrip()}\n\n{untracked}".strip()
    additions = 0
    deletions = 0
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    existing = _existing_pr(path, workspace.branch)
    return WorkspaceReview(
        workspace_id=workspace.id,
        branch=workspace.branch,
        clean=len(files) == 0,
        files=files,
        additions=additions,
        deletions=deletions,
        diff=diff,
        pull_request_url=str(existing["url"]) if existing else None,
        pull_request_number=existing["number"] if existing and isinstance(existing["number"], int) else None,
    )


def has_reviewable_changes(db: Session, workspace_id: str) -> bool:
    return not workspace_review(db, workspace_id).clean


def publish_workspace(db: Session, workspace_id: str) -> WorkspacePublishResult:
    workspace = require_workspace(db, workspace_id)
    if not workspace.ticket_id:
        raise HTTPException(status_code=409, detail="Workspace is not associated with a ticket")
    path = _workspace_path(workspace)
    ticket = require_ticket(db, workspace.ticket_id)
    repository = require_repository(db, workspace.repository_id)
    review = workspace_review(db, workspace.id)

    existing = _existing_pr(path, workspace.branch)
    if existing is not None:
        return WorkspacePublishResult(
            branch=workspace.branch,
            commit_sha=None,
            pull_request_url=str(existing["url"]),
            pull_request_number=existing["number"] if isinstance(existing["number"], int) else None,
            created=False,
        )

    if review.clean:
        raise HTTPException(status_code=409, detail="Workspace has no reviewable changes to publish")

    # .agentdesk is already ignored by Git. Do not pass the ignored path as an
    # explicit negative pathspec to `git add`; Git treats that as an attempt to
    # address an ignored path and aborts before the commit/PR can be created.
    _run(["git", "add", "-A", "--", "."], cwd=path)
    title = ticket.title
    prefix = f"{ticket.ticket_key} "
    if title.startswith(prefix):
        title = title[len(prefix):]
    commit_title = f"{ticket.ticket_key}: {title}"
    _run(["git", "commit", "-m", commit_title], cwd=path)
    commit_sha = _run(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()
    _run(["git", "push", "-u", "origin", workspace.branch], cwd=path)

    body = (
        f"AgentDesk ticket **{ticket.ticket_key}**\n\n"
        f"{ticket.goal or ticket.description or title}\n\n"
        "Created from the AgentDesk review workflow. Merge remains a human decision in GitHub."
    )
    created = _run(
        ["gh", "pr", "create", "--base", repository.default_branch, "--head", workspace.branch, "--title", commit_title, "--body", body],
        cwd=path,
    )
    url = created.stdout.strip().splitlines()[-1].strip()
    number: int | None = None
    existing = _existing_pr(path, workspace.branch)
    if existing is not None:
        url = str(existing["url"])
        number = existing["number"] if isinstance(existing["number"], int) else None

    event_repository.add(
        db,
        TicketEvent(
            ticket_id=ticket.id,
            event_type="pull_request_created",
            actor="user",
            payload={"workspace_id": workspace.id, "branch": workspace.branch, "commit_sha": commit_sha, "url": url, "number": number},
        ),
    )
    if ticket.status != TicketStatus.REVIEW:
        update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.REVIEW))

    return WorkspacePublishResult(
        branch=workspace.branch,
        commit_sha=commit_sha,
        pull_request_url=url,
        pull_request_number=number,
        created=True,
    )


def sync_pull_request(db: Session, workspace_id: str) -> dict[str, object]:
    workspace = require_workspace(db, workspace_id)
    if not workspace.ticket_id:
        raise HTTPException(status_code=409, detail="Workspace is not associated with a ticket")
    path = _workspace_path(workspace)
    pr = _existing_pr(path, workspace.branch)
    if pr is None:
        return {"found": False, "merged": False, "cleaned_up": False}
    if not pr["merged"]:
        return {"found": True, "merged": False, "cleaned_up": False, "url": pr["url"], "number": pr["number"], "state": pr["state"]}

    ticket = require_ticket(db, workspace.ticket_id)
    repository = require_repository(db, workspace.repository_id)
    branch = workspace.branch
    url = str(pr["url"])
    number = pr["number"] if isinstance(pr["number"], int) else None

    remove_workspace(db, workspace.id)
    managed_clone = Path(repository.managed_path).resolve() if repository.managed_path else None
    if managed_clone and managed_clone.exists():
        _run(["git", "push", "origin", "--delete", branch], cwd=managed_clone, allow_failure=True)
        _run(["git", "branch", "-D", branch], cwd=managed_clone, allow_failure=True)
        _run(["git", "fetch", "--prune", "origin"], cwd=managed_clone, allow_failure=True)

    update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.DONE))
    event_repository.add(
        db,
        TicketEvent(
            ticket_id=ticket.id,
            event_type="pull_request_merged",
            actor="system",
            payload={"workspace_id": workspace.id, "branch": branch, "url": url, "number": number, "branch_cleaned_up": True},
        ),
    )
    return {"found": True, "merged": True, "cleaned_up": True, "url": url, "number": number, "state": "merged"}
