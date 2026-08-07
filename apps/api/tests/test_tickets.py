from fastapi.testclient import TestClient

from agentdesk_api.main import app


def create_project(client: TestClient, name: str = "AgentDesk") -> dict:
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_ticket_crud_hierarchy_and_project_scoped_keys() -> None:
    with TestClient(app) as client:
        project = create_project(client)
        epic_response = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Ticket core", "type": "epic", "priority": "high"},
        )
        assert epic_response.status_code == 201
        epic = epic_response.json()
        assert epic["ticket_key"] == "AD-1"
        assert epic["sequence"] == 1
        assert epic["status"] == "backlog"
        assert epic["priority"] == "high"

        story_response = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Persist tickets", "type": "story", "parent_id": epic["id"], "order": 10},
        )
        assert story_response.status_code == 201
        story = story_response.json()
        assert story["ticket_key"] == "AD-2"
        assert story["parent_id"] == epic["id"]

        listed = client.get(f"/projects/{project['id']}/tickets")
        assert listed.status_code == 200
        assert [ticket["ticket_key"] for ticket in listed.json()] == ["AD-1", "AD-2"]

        fetched = client.get(f"/tickets/{story['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["title"] == "Persist tickets"

        updated = client.patch(
            f"/tickets/{story['id']}",
            json={"status": "in_progress", "priority": "critical", "description": "Working now"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "in_progress"
        assert updated.json()["priority"] == "critical"
        assert updated.json()["description"] == "Working now"


def test_all_ticket_types_and_statuses_are_accepted() -> None:
    with TestClient(app) as client:
        project = create_project(client, "Types")
        types = ["epic", "story", "task", "bug", "spike"]
        statuses = ["backlog", "ready", "in_progress", "review", "done", "blocked", "needs_human", "agent_failed"]

        for ticket_type in types:
            response = client.post(
                f"/projects/{project['id']}/tickets",
                json={"title": f"{ticket_type} ticket", "type": ticket_type},
            )
            assert response.status_code == 201
            assert response.json()["type"] == ticket_type

        ticket_id = client.get(f"/projects/{project['id']}/tickets").json()[0]["id"]
        for ticket_status in statuses:
            response = client.patch(f"/tickets/{ticket_id}", json={"status": ticket_status})
            assert response.status_code == 200
            assert response.json()["status"] == ticket_status


def test_parent_must_belong_to_same_project() -> None:
    with TestClient(app) as client:
        first = create_project(client, "First Project")
        second = create_project(client, "Second Project")
        parent = client.post(
            f"/projects/{first['id']}/tickets", json={"title": "Parent", "type": "epic"}
        ).json()
        response = client.post(
            f"/projects/{second['id']}/tickets", json={"title": "Wrong child", "parent_id": parent["id"]}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Parent ticket must belong to the same project"


def test_ticket_keys_are_numbered_independently_per_project() -> None:
    with TestClient(app) as client:
        alpha = create_project(client, "Alpha Desk")
        beta = create_project(client, "Beta Board")
        alpha_ticket = client.post(
            f"/projects/{alpha['id']}/tickets", json={"title": "Alpha ticket"}
        ).json()
        beta_ticket = client.post(
            f"/projects/{beta['id']}/tickets", json={"title": "Beta ticket"}
        ).json()
        assert alpha_ticket["ticket_key"] == "AD-1"
        assert beta_ticket["ticket_key"] == "BB-1"


def test_missing_ticket_and_invalid_parent_return_errors() -> None:
    with TestClient(app) as client:
        project = create_project(client, "Errors")
        assert client.get("/tickets/not-a-real-id").status_code == 404
        invalid_parent = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Child", "parent_id": "not-a-real-id"},
        )
        assert invalid_parent.status_code == 400


def test_ticket_hierarchy_rejects_cycles() -> None:
    with TestClient(app) as client:
        project = create_project(client, "Hierarchy")
        parent = client.post(
            f"/projects/{project['id']}/tickets", json={"title": "Parent", "type": "epic"}
        ).json()
        child = client.post(
            f"/projects/{project['id']}/tickets", json={"title": "Child", "parent_id": parent["id"]}
        ).json()
        response = client.patch(f"/tickets/{parent['id']}", json={"parent_id": child["id"]})
        assert response.status_code == 400
        assert response.json()["detail"] == "Ticket hierarchy cannot contain a cycle"
