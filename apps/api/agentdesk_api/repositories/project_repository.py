from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Project


def get(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


def list_all(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at)).all())


def save(db: Session, project: Project) -> Project:
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
