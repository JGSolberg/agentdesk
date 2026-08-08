from fastapi.testclient import TestClient

from agentdesk_api.main import app


def test_cancel_archive_unarchive_and_delete_ticket() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Lifecycle"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Disposable ticket"}).json()

        cancelled = client.patch(f"/tickets/{ticket['id']}", json={"status": "cancelled"})
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        events = client.get(f"/tickets/{ticket['id']}/events").json()
        assert any(event["event_type"] == "ticket_cancelled" for event in events)

        reopened = client.patch(f"/tickets/{ticket['id']}", json={"status": "backlog"})
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "backlog"

        archived = client.patch(f"/tickets/{ticket['id']}", json={"archived": True})
        assert archived.status_code == 200
        assert archived.json()["archived"] is True
        assert client.get(f"/projects/{project['id']}/tickets").json() == []
        assert len(client.get(f"/projects/{project['id']}/tickets?include_archived=true").json()) == 1

        unarchived = client.patch(f"/tickets/{ticket['id']}", json={"archived": False})
        assert unarchived.status_code == 200
        assert unarchived.json()["archived"] is False

        deleted = client.delete(f"/tickets/{ticket['id']}")
        assert deleted.status_code == 204
        assert client.get(f"/tickets/{ticket['id']}").status_code == 404


def test_delete_ticket_is_guarded_by_children_and_dependencies() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Delete Guards"}).json()
        parent = client.post(f"/projects/{project['id']}/tickets", json={"title": "Parent"}).json()
        child = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Child", "parent_id": parent["id"]},
        ).json()

        blocked = client.delete(f"/tickets/{parent['id']}")
        assert blocked.status_code == 409
        assert "child" in blocked.json()["detail"].lower()

        other = client.post(f"/projects/{project['id']}/tickets", json={"title": "Dependency"}).json()
        assert client.post(f"/tickets/{child['id']}/dependencies/{other['id']}").status_code == 200
        dependency_blocked = client.delete(f"/tickets/{other['id']}")
        assert dependency_blocked.status_code == 409
        assert "dependency" in dependency_blocked.json()["detail"].lower()
