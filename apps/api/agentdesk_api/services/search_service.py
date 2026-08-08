from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import Project, Repository, Ticket
from ..schemas import SearchResult


def search(db: Session, query: str, limit: int = 20) -> list[SearchResult]:
    term = query.strip()
    if not term:
        return []

    pattern = f"%{term}%"
    results: list[SearchResult] = []

    tickets = db.scalars(
        select(Ticket)
        .where(or_(Ticket.ticket_key.ilike(pattern), Ticket.title.ilike(pattern)))
        .order_by(Ticket.archived, Ticket.ticket_key)
        .limit(limit)
    ).all()
    for ticket in tickets:
        results.append(
            SearchResult(
                kind="ticket",
                id=ticket.id,
                label=f"{ticket.ticket_key} · {ticket.title}",
                subtitle=f"{ticket.type.value} · {ticket.status.value.replace('_', ' ')}",
                href=f"/tickets/{ticket.id}",
                archived=ticket.archived,
            )
        )

    remaining = max(0, limit - len(results))
    if remaining:
        projects = db.scalars(
            select(Project).where(Project.name.ilike(pattern)).order_by(Project.name).limit(remaining)
        ).all()
        for project in projects:
            results.append(
                SearchResult(
                    kind="project",
                    id=project.id,
                    label=project.name,
                    subtitle="Project",
                    href=f"/projects/{project.id}",
                    archived=project.archived,
                )
            )

    remaining = max(0, limit - len(results))
    if remaining:
        repositories = db.scalars(
            select(Repository)
            .where(or_(Repository.name.ilike(pattern), Repository.remote_url.ilike(pattern)))
            .order_by(Repository.name)
            .limit(remaining)
        ).all()
        for repository in repositories:
            results.append(
                SearchResult(
                    kind="repository",
                    id=repository.id,
                    label=repository.name,
                    subtitle=repository.remote_url,
                    href=f"/projects/{repository.project_id}/repositories",
                )
            )

    return results[:limit]
