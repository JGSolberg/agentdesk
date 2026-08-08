from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GitArtifact, Repository, TicketEvent
from ..repositories import event_repository
from ..schemas import GitArtifactCreate, GitArtifactUpdate
from .ticket_service import require_ticket


def _validate_repository(db: Session, ticket_project_id: str, repository_id: str | None) -> None:
    if repository_id is None:
        return
    repository = db.get(Repository, repository_id)
    if repository is None or repository.project_id != ticket_project_id:
        raise HTTPException(status_code=400, detail="Repository must belong to the ticket project")


def list_artifacts(db: Session, ticket_id: str) -> list[GitArtifact]:
    require_ticket(db, ticket_id)
    return list(db.scalars(select(GitArtifact).where(GitArtifact.ticket_id == ticket_id).order_by(GitArtifact.created_at)).all())


def create_artifact(db: Session, ticket_id: str, payload: GitArtifactCreate) -> GitArtifact:
    ticket = require_ticket(db, ticket_id)
    _validate_repository(db, ticket.project_id, payload.repository_id)
    values = payload.model_dump(exclude={"metadata"})
    artifact = GitArtifact(ticket_id=ticket_id, metadata_=payload.metadata, **values)
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    event_repository.add(db, TicketEvent(ticket_id=ticket_id, event_type="git_artifact_created", payload={"artifact_id": artifact.id, "kind": artifact.kind.value, "identifier": artifact.identifier}))
    return artifact


def update_artifact(db: Session, artifact_id: str, payload: GitArtifactUpdate) -> GitArtifact:
    artifact = db.get(GitArtifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Git artifact not found")
    ticket = require_ticket(db, artifact.ticket_id)
    changes: dict = {}
    values = payload.model_dump(exclude_unset=True)
    if "repository_id" in values:
        _validate_repository(db, ticket.project_id, values["repository_id"])
    for field, value in values.items():
        attribute = "metadata_" if field == "metadata" else field
        before = getattr(artifact, attribute)
        if before != value:
            changes[field] = {"from": before, "to": value}
            setattr(artifact, attribute, value)
    if changes:
        db.commit()
        db.refresh(artifact)
        event_repository.add(db, TicketEvent(ticket_id=artifact.ticket_id, event_type="git_artifact_updated", payload={"artifact_id": artifact.id, "kind": artifact.kind.value, "identifier": artifact.identifier, "changes": changes}))
    return artifact
