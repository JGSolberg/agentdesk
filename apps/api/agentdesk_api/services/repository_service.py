from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Repository
from ..repositories import repository_repository
from ..schemas import RepositoryCreate, RepositoryUpdate
from .project_service import require_project


def require_repository(db: Session, repository_id: str) -> Repository:
    repository = repository_repository.get(db, repository_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repository


def list_repositories(db: Session, project_id: str) -> list[Repository]:
    require_project(db, project_id)
    return repository_repository.list_for_project(db, project_id)


def _clear_other_primary(db: Session, project_id: str, repository_id: str | None = None) -> None:
    for repository in repository_repository.list_for_project(db, project_id):
        if repository.id != repository_id and repository.is_primary:
            repository.is_primary = False
            db.add(repository)


def _agentdesk_home() -> Path:
    configured = os.getenv("AGENTDESK_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".agentdesk").resolve()


def managed_clone_path(repository: Repository) -> Path:
    return _agentdesk_home() / "repositories" / repository.id / "clone"


def create_repository(db: Session, project_id: str, payload: RepositoryCreate) -> Repository:
    require_project(db, project_id)
    existing = repository_repository.list_for_project(db, project_id)
    make_primary = payload.is_primary or not existing
    if make_primary:
        _clear_other_primary(db, project_id)
    repository = Repository(
        project_id=project_id,
        **payload.model_dump(exclude={"is_primary"}),
        is_primary=make_primary,
    )
    return repository_repository.save(db, repository)


def update_repository(db: Session, repository_id: str, payload: RepositoryUpdate) -> Repository:
    repository = require_repository(db, repository_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("is_primary"):
        _clear_other_primary(db, repository.project_id, repository.id)
    if "remote_url" in changes and changes["remote_url"] != repository.remote_url and repository.managed_path:
        raise HTTPException(status_code=409, detail="Remove the managed clone before changing its remote URL")
    for field, value in changes.items():
        setattr(repository, field, value)
    return repository_repository.save(db, repository)


def clone_or_refresh_repository(db: Session, repository_id: str) -> Repository:
    repository = require_repository(db, repository_id)
    path = managed_clone_path(repository)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if path.exists():
            if not (path / ".git").exists():
                raise HTTPException(status_code=409, detail="Managed clone path exists but is not a Git repository")
            subprocess.run(["git", "-C", str(path), "fetch", "--prune", "origin"], check=True, capture_output=True, text=True)
        else:
            subprocess.run(
                ["git", "clone", "--branch", repository.default_branch, "--single-branch", repository.remote_url, str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Git executable was not found") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "Git operation failed"
        raise HTTPException(status_code=502, detail=detail) from exc

    repository.managed_path = str(path)
    return repository_repository.save(db, repository)


def remove_managed_clone(db: Session, repository_id: str) -> Repository:
    repository = require_repository(db, repository_id)
    if not repository.managed_path:
        return repository

    path = Path(repository.managed_path).resolve()
    root = (_agentdesk_home() / "repositories" / repository.id).resolve()
    if path != root / "clone" or root not in path.parents:
        raise HTTPException(status_code=409, detail="Refusing to remove a path not owned by AgentDesk")
    if path.exists():
        shutil.rmtree(path)
    repository.managed_path = None
    return repository_repository.save(db, repository)


def delete_repository(db: Session, repository_id: str) -> None:
    repository = require_repository(db, repository_id)
    if repository.managed_path:
        raise HTTPException(status_code=409, detail="Remove the managed clone before deleting this repository registration")
    was_primary = repository.is_primary
    project_id = repository.project_id
    repository_repository.delete(db, repository)
    if was_primary:
        remaining = repository_repository.list_for_project(db, project_id)
        if remaining:
            remaining[0].is_primary = True
            repository_repository.save(db, remaining[0])
