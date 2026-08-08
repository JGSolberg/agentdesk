from __future__ import annotations

from pathlib import Path
import subprocess

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Workspace
from .repository_service import require_repository


def _run(args: list[str], *, cwd: Path, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Executable was not found: {args[0]}") from exc
    if result.returncode != 0 and not allow_failure:
        raise HTTPException(status_code=502, detail=result.stderr.strip() or result.stdout.strip() or f"{args[0]} failed")
    return result


def refresh_default_branch(db: Session, workspace: Workspace) -> str:
    repository = require_repository(db, workspace.repository_id)
    path = Path(workspace.path).resolve()
    if not path.exists():
        raise HTTPException(status_code=409, detail="Workspace path is missing")
    _run(["git", "fetch", "--prune", "origin", repository.default_branch], cwd=path)
    return repository.default_branch


def has_unmerged_conflicts(workspace: Workspace) -> bool:
    path = Path(workspace.path).resolve()
    result = _run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=path, allow_failure=True)
    return bool(result.stdout.strip())
