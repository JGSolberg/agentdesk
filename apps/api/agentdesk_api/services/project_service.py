from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Project
from ..repositories import project_repository
from ..schemas import ProjectCreate, ProjectUpdate


def require_project(db: Session, project_id: str) -> Project:
    project = project_repository.get(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def create_project(db: Session, payload: ProjectCreate) -> Project:
    return project_repository.save(
        db,
        Project(name=payload.name, description=payload.description),
    )


def list_projects(db: Session) -> list[Project]:
    return project_repository.list_all(db)


def update_project(db: Session, project_id: str, payload: ProjectUpdate) -> Project:
    project = require_project(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    return project_repository.save(db, project)
