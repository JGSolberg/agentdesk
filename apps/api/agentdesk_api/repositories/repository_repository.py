from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Repository


def get(db: Session, repository_id: str) -> Repository | None:
    return db.get(Repository, repository_id)


def list_for_project(db: Session, project_id: str) -> list[Repository]:
    query = select(Repository).where(Repository.project_id == project_id).order_by(Repository.is_primary.desc(), Repository.name)
    return list(db.scalars(query).all())


def save(db: Session, repository: Repository) -> Repository:
    db.add(repository)
    db.commit()
    db.refresh(repository)
    return repository


def delete(db: Session, repository: Repository) -> None:
    db.delete(repository)
    db.commit()
