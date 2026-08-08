from fastapi.testclient import TestClient

from agentdesk_api.database import SessionLocal
from agentdesk_api.main import app
from agentdesk_api.models import Repository
from agentdesk_api.services import workspace_service


def test_workspace_requires_managed_clone() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Workspace Project"}).json()
        repository = client.post(
            f"/projects/{project['id']}/repositories",
            json={
                "name": "workspace-repo",
                "provider": "other",
                "remote_url": "example.invalid/workspace-repo.git",
                "default_branch": "main",
            },
        ).json()

        listed = client.get(f"/repositories/{repository['id']}/workspaces")
        assert listed.status_code == 200
        assert listed.json() == []

        response = client.post(
            f"/repositories/{repository['id']}/workspaces",
            json={"branch": "agent/example"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Clone the repository before creating a workspace"


def test_workspace_repository_must_exist() -> None:
    with TestClient(app) as client:
        response = client.get("/repositories/missing/workspaces")
        assert response.status_code == 404


def test_ticket_workspace_records_activity(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(workspace_service, "_git", lambda *args, **kwargs: None)
    monkeypatch.setenv("AGENTDESK_HOME", str(tmp_path / "agentdesk-home"))

    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Workspace Events"}).json()
        ticket = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Workspace event ticket"},
        ).json()
        repository = client.post(
            f"/projects/{project['id']}/repositories",
            json={
                "name": "event-repo",
                "provider": "other",
                "remote_url": "example.invalid/event-repo.git",
                "default_branch": "main",
            },
        ).json()

        with SessionLocal() as db:
            stored = db.get(Repository, repository["id"])
            assert stored is not None
            stored.managed_path = str(tmp_path / "managed-clone")
            db.add(stored)
            db.commit()

        created = client.post(
            f"/repositories/{repository['id']}/workspaces",
            json={"ticket_id": ticket["id"]},
        )
        assert created.status_code == 201
        workspace = created.json()

        events = client.get(f"/tickets/{ticket['id']}/events").json()
        assert any(event["event_type"] == "workspace_created" and event["payload"]["branch"] == f"agent/{ticket['ticket_key']}" for event in events)

        removed = client.delete(f"/workspaces/{workspace['id']}")
        assert removed.status_code == 200

        events = client.get(f"/tickets/{ticket['id']}/events").json()
        assert any(event["event_type"] == "workspace_removed" and event["payload"]["workspace_id"] == workspace["id"] for event in events)
