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


def create_repository(db: Session, project_id: str, payload: RepositoryCreate) -> Repository:
    require_project(db, project_id)
    existing = repository_repository.list_for_project(db, project_id)
    make_primary = payload.is_primary or not existing
    if make_primary:
        _clear_other_primary(db, project_id)
    repository = Repository(project_id=project_id, **payload.model_dump(exclude={"is_primary"}), is_primary=make_primary)
    return repository_repository.save(db, repository)


def update_repository(db: Session, repository_id: str, payload: RepositoryUpdate) -> Repository:
    repository = require_repository(db, repository_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("is_primary"):
        _clear_other_primary(db, repository.project_id, repository.id)
    for field, value in changes.items():
        setattr(repository, field, value)
    return repository_repository.save(db, repository)


def delete_repository(db: Session, repository_id: str) -> None:
    repository = require_repository(db, repository_id)
    was_primary = repository.is_primary
    project_id = repository.project_id
    repository_repository.delete(db, repository)
    if was_primary:
        remaining = repository_repository.list_for_project(db, project_id)
        if remaining:
            remaining[0].is_primary = True
            repository_repository.save(db, remaining[0])
