from fastapi.testclient import TestClient

from agentdesk_api.main import app


def test_project_crud() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/projects",
            json={"name": "AgentDesk", "description": "Build the engineering cockpit"},
        )
        assert created.status_code == 201
        project = created.json()
        assert project["name"] == "AgentDesk"
        assert project["archived"] is False

        listed = client.get("/projects")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [project["id"]]

        fetched = client.get(f"/projects/{project['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["description"] == "Build the engineering cockpit"

        updated = client.patch(
            f"/projects/{project['id']}",
            json={"name": "AgentDesk V1", "archived": True},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "AgentDesk V1"
        assert updated.json()["archived"] is True


def test_missing_project_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/projects/not-a-real-id")
        assert response.status_code == 404
