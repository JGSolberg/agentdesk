from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class GitRepositoryStatus:
    path_exists: bool
    is_git_repository: bool
    branch: str | None = None
    head_sha: str | None = None
    head_message: str | None = None
    remote_url: str | None = None
    is_dirty: bool = False
    staged_count: int = 0
    modified_count: int = 0
    untracked_count: int = 0
    error: str | None = None


def _git(path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def inspect_repository(local_path: str) -> GitRepositoryStatus:
    path = Path(local_path).expanduser()
    if not path.exists() or not path.is_dir():
        return GitRepositoryStatus(
            path_exists=False,
            is_git_repository=False,
            error="Directory not found",
        )

    try:
        inside = _git(path, "rev-parse", "--is-inside-work-tree", check=False)
    except FileNotFoundError:
        return GitRepositoryStatus(
            path_exists=True,
            is_git_repository=False,
            error="Git executable not found",
        )

    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return GitRepositoryStatus(
            path_exists=True,
            is_git_repository=False,
            error="Not a Git repository",
        )

    try:
        branch_result = _git(path, "branch", "--show-current", check=False)
        branch = branch_result.stdout.strip() or None

        head_result = _git(path, "log", "-1", "--format=%H%x00%s", check=False)
        head_sha: str | None = None
        head_message: str | None = None
        if head_result.returncode == 0 and head_result.stdout.strip():
            head_parts = head_result.stdout.strip().split("\x00", 1)
            head_sha = head_parts[0] or None
            head_message = head_parts[1] if len(head_parts) > 1 else None

        remote_result = _git(path, "remote", "get-url", "origin", check=False)
        remote_url = remote_result.stdout.strip() if remote_result.returncode == 0 else None

        status_result = _git(path, "status", "--porcelain=v1", "--untracked-files=all")
        staged_count = 0
        modified_count = 0
        untracked_count = 0
        for line in status_result.stdout.splitlines():
            if line.startswith("??"):
                untracked_count += 1
                continue
            if len(line) < 2:
                continue
            index_state, worktree_state = line[0], line[1]
            if index_state != " ":
                staged_count += 1
            if worktree_state != " ":
                modified_count += 1

        return GitRepositoryStatus(
            path_exists=True,
            is_git_repository=True,
            branch=branch,
            head_sha=head_sha,
            head_message=head_message,
            remote_url=remote_url,
            is_dirty=bool(staged_count or modified_count or untracked_count),
            staged_count=staged_count,
            modified_count=modified_count,
            untracked_count=untracked_count,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "Git inspection failed"
        return GitRepositoryStatus(
            path_exists=True,
            is_git_repository=True,
            error=detail,
        )
