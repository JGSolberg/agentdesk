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


def _is_git_worktree(path: Path) -> bool:
    if not path.exists():
        return False
    return _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, allow_failure=True).returncode == 0


def _existing_pr(path: Path, branch: str) -> dict[str, object] | None:
    try:
        result = _run(["gh", "pr", "view", branch, "--json", "url,number,state,mergedAt,headRefOid"], cwd=path, allow_failure=True)
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
        "head_sha": str(payload.get("headRefOid") or "").strip() or None,
    }


def _pr_lookup_path(workspace: Workspace, repository_managed_path: str | None) -> Path:
    workspace_path = Path(workspace.path).resolve()
    if _is_git_worktree(workspace_path):
        return workspace_path
    if repository_managed_path:
        managed = Path(repository_managed_path).resolve()
        if managed.exists():
            return managed
    return workspace_path


def _status_lines(path: Path) -> list[str]:
    result = _run(["git", "status", "--porcelain=v1", "--untracked-files=all", "--", ".", _EXCLUDE_PATHSPEC], cwd=path)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _base_ref(path: Path, default_branch: str) -> str:
    candidate = f"origin/{default_branch}"
    verified = _run(["git", "rev-parse", "--verify", candidate], cwd=path, allow_failure=True)
    return candidate if verified.returncode == 0 else "HEAD"


def _review_files(path: Path, base_ref: str) -> list[WorkspaceReviewFile]:
    files: dict[str, WorkspaceReviewFile] = {}
    committed = _run(["git", "diff", "--name-status", base_ref, "--", ".", _EXCLUDE_PATHSPEC], cwd=path, allow_failure=True)
    for line in committed.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files[parts[-1]] = WorkspaceReviewFile(path=parts[-1], status=parts[0])
    for line in _status_lines(path):
        code = line[:2]
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1]
        files[raw_path] = WorkspaceReviewFile(path=raw_path, status=code)
    return list(files.values())


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
        chunks.append("".join(difflib.unified_diff([], text.splitlines(keepends=True), fromfile=f"a/{item.path}", tofile=f"b/{item.path}", lineterm="\n")))
    return "\n".join(chunk for chunk in chunks if chunk)


def _has_unmerged_conflicts(path: Path) -> bool:
    return bool(_run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=path, allow_failure=True).stdout.strip())


def _has_unpublished_work(path: Path, existing_pr: dict[str, object] | None) -> bool:
    if existing_pr and bool(existing_pr.get("merged")):
        return False
    if _status_lines(path):
        return True
    head = _run(["git", "rev-parse", "HEAD"], cwd=path, allow_failure=True)
    if head.returncode != 0:
        return False
    local_head = head.stdout.strip()
    if existing_pr is not None:
        remote_head = str(existing_pr.get("head_sha") or "").strip()
        if remote_head:
            return local_head != remote_head
    upstream = _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], cwd=path, allow_failure=True)
    if upstream.returncode != 0:
        return False
    ahead = _run(["git", "rev-list", "--count", "@{upstream}..HEAD"], cwd=path, allow_failure=True)
    return ahead.returncode == 0 and int(ahead.stdout.strip() or "0") > 0


def workspace_review(db: Session, workspace_id: str) -> WorkspaceReview:
    workspace = require_workspace(db, workspace_id)
    repository = require_repository(db, workspace.repository_id)
    path = Path(workspace.path).resolve()
    lookup_path = _pr_lookup_path(workspace, repository.managed_path)
    existing = _existing_pr(lookup_path, workspace.branch)

    # A previous cleanup attempt may have removed Git's worktree metadata while
    # leaving the DB workspace active. Keep the ticket recoverable: surface the
    # PR state and let Sync & finalize finish cleanup instead of running Git in
    # a directory whose .git pointer is now stale.
    if not _is_git_worktree(path):
        return WorkspaceReview(
            workspace_id=workspace.id,
            branch=workspace.branch,
            clean=True,
            unpublished=False,
            files=[],
            additions=0,
            deletions=0,
            diff="",
            pull_request_url=str(existing["url"]) if existing else None,
            pull_request_number=existing["number"] if existing and isinstance(existing["number"], int) else None,
            pull_request_merged=bool(existing and existing.get("merged")),
        )

    base_ref = _base_ref(path, repository.default_branch)
    files = _review_files(path, base_ref)
    diff = _run(["git", "diff", base_ref, "--", ".", _EXCLUDE_PATHSPEC], cwd=path).stdout
    untracked = _untracked_diff(path, files)
    if untracked:
        diff = f"{diff.rstrip()}\n\n{untracked}".strip()
    additions = deletions = 0
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return WorkspaceReview(
        workspace_id=workspace.id,
        branch=workspace.branch,
        clean=len(files) == 0,
        unpublished=_has_unpublished_work(path, existing),
        files=files,
        additions=additions,
        deletions=deletions,
        diff=diff,
        pull_request_url=str(existing["url"]) if existing else None,
        pull_request_number=existing["number"] if existing and isinstance(existing["number"], int) else None,
        pull_request_merged=bool(existing and existing.get("merged")),
    )


def has_reviewable_changes(db: Session, workspace_id: str) -> bool:
    return not workspace_review(db, workspace_id).clean


def publish_workspace(db: Session, workspace_id: str) -> WorkspacePublishResult:
    workspace = require_workspace(db, workspace_id)
    if not workspace.ticket_id:
        raise HTTPException(status_code=409, detail="Workspace is not associated with a ticket")
    path = _workspace_path(workspace)
    if not _is_git_worktree(path):
        raise HTTPException(status_code=409, detail="Workspace Git metadata is unavailable. Sync PR status to finalize or recreate the workspace.")
    ticket = require_ticket(db, workspace.ticket_id)
    repository = require_repository(db, workspace.repository_id)
    existing = _existing_pr(path, workspace.branch)
    if existing is not None and bool(existing.get("merged")):
        raise HTTPException(status_code=409, detail="Pull request is already merged. Sync PR status to finalize the ticket and clean up the workspace.")

    origin = _run(["git", "remote", "get-url", "origin"], cwd=path, allow_failure=True)
    if origin.returncode == 0:
        _run(["git", "fetch", "--prune", "origin", repository.default_branch], cwd=path)
        if _has_unmerged_conflicts(path):
            raise HTTPException(status_code=409, detail="Workspace still has unresolved merge conflicts. Run the agent again before publishing.")
        base_ref = f"origin/{repository.default_branch}"
        current = _run(["git", "merge-base", "--is-ancestor", base_ref, "HEAD"], cwd=path, allow_failure=True)
        if current.returncode != 0:
            raise HTTPException(status_code=409, detail=f"Workspace is not integrated with the latest {base_ref}. Run the agent again so it can resolve default-branch conflicts before publishing.")

    review = workspace_review(db, workspace.id)
    existing = _existing_pr(path, workspace.branch)
    if review.clean and existing is not None:
        return WorkspacePublishResult(branch=workspace.branch, commit_sha=None, pull_request_url=str(existing["url"]), pull_request_number=existing["number"] if isinstance(existing["number"], int) else None, created=False)
    if review.clean:
        raise HTTPException(status_code=409, detail="Workspace has no reviewable changes to publish")

    _run(["git", "add", "-A", "--", "."], cwd=path)
    title = ticket.title
    prefix = f"{ticket.ticket_key} "
    if title.startswith(prefix):
        title = title[len(prefix):]
    commit_title = f"{ticket.ticket_key}: {title}"
    staged = _run(["git", "diff", "--cached", "--quiet"], cwd=path, allow_failure=True)
    if staged.returncode != 0:
        _run(["git", "commit", "-m", commit_title], cwd=path)
    commit_sha = _run(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()
    _run(["git", "push", "-u", "origin", workspace.branch], cwd=path)

    if existing is not None:
        return WorkspacePublishResult(branch=workspace.branch, commit_sha=commit_sha, pull_request_url=str(existing["url"]), pull_request_number=existing["number"] if isinstance(existing["number"], int) else None, created=False)

    body = f"AgentDesk ticket **{ticket.ticket_key}**\n\n{ticket.goal or ticket.description or title}\n\nCreated from the AgentDesk review workflow. Merge remains a human decision in GitHub."
    created = _run(["gh", "pr", "create", "--base", repository.default_branch, "--head", workspace.branch, "--title", commit_title, "--body", body], cwd=path)
    url = created.stdout.strip().splitlines()[-1].strip()
    number: int | None = None
    existing = _existing_pr(path, workspace.branch)
    if existing is not None:
        url = str(existing["url"])
        number = existing["number"] if isinstance(existing["number"], int) else None

    event_repository.add(db, TicketEvent(ticket_id=ticket.id, event_type="pull_request_created", actor="user", payload={"workspace_id": workspace.id, "branch": workspace.branch, "commit_sha": commit_sha, "url": url, "number": number}))
    if ticket.status != TicketStatus.REVIEW:
        update_ticket(db, ticket.id, TicketUpdate(status=TicketStatus.REVIEW))
    return WorkspacePublishResult(branch=workspace.branch, commit_sha=commit_sha, pull_request_url=url, pull_request_number=number, created=True)


def sync_pull_request(db: Session, workspace_id: str) -> dict[str, object]:
    workspace = require_workspace(db, workspace_id)
    if not workspace.ticket_id:
        raise HTTPException(status_code=409, detail="Workspace is not associated with a ticket")
    repository = require_repository(db, workspace.repository_id)
    lookup_path = _pr_lookup_path(workspace, repository.managed_path)
    pr = _existing_pr(lookup_path, workspace.branch)
    if pr is None:
        return {"found": False, "merged": False, "cleaned_up": False}
    if not pr["merged"]:
        return {"found": True, "merged": False, "cleaned_up": False, "url": pr["url"], "number": pr["number"], "state": pr["state"]}

    ticket = require_ticket(db, workspace.ticket_id)
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
    event_repository.add(db, TicketEvent(ticket_id=ticket.id, event_type="pull_request_merged", actor="system", payload={"workspace_id": workspace.id, "branch": branch, "url": url, "number": number, "branch_cleaned_up": True}))
    return {"found": True, "merged": True, "cleaned_up": True, "url": url, "number": number, "state": "merged"}
