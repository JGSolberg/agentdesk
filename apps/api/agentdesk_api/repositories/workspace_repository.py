from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Workspace, WorkspaceStatus


def get(db: Session, workspace_id: str) -> Workspace | None:
    return db.get(Workspace, workspace_id)


def list_for_repository(db: Session, repository_id: str, *, active_only: bool = False) -> list[Workspace]:
    query = select(Workspace).where(Workspace.repository_id == repository_id)
    if active_only:
        query = query.where(Workspace.status == WorkspaceStatus.ACTIVE)
    return list(db.scalars(query.order_by(Workspace.created_at)).all())


def save(db: Session, workspace: Workspace) -> Workspace:
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace
