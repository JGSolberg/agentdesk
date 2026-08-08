from fastapi.testclient import TestClient

from agentdesk_api.main import app


def test_global_search_finds_tickets_projects_repositories_and_archived_tickets() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "AgentDesk Search"}).json()
        ticket = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Build command palette", "type": "story"},
        ).json()
        archived_ticket = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Old searchable ticket", "type": "task"},
        ).json()
        client.patch(f"/tickets/{archived_ticket['id']}", json={"archived": True})
        repository = client.post(
            f"/projects/{project['id']}/repositories",
            json={
                "name": "agentdesk-search-repo",
                "provider": "github",
                "remote_url": "https://github.com/example/agentdesk-search-repo",
                "default_branch": "main",
            },
        ).json()

        by_key = client.get("/search", params={"q": ticket["ticket_key"]})
        assert by_key.status_code == 200
        assert by_key.json()[0]["id"] == ticket["id"]
        assert by_key.json()[0]["kind"] == "ticket"

        by_title = client.get("/search", params={"q": "command palette"})
        assert any(item["id"] == ticket["id"] for item in by_title.json())

        by_project = client.get("/search", params={"q": "AgentDesk Search"})
        assert any(item["kind"] == "project" and item["id"] == project["id"] for item in by_project.json())

        by_repository = client.get("/search", params={"q": "search-repo"})
        assert any(item["kind"] == "repository" and item["id"] == repository["id"] for item in by_repository.json())

        archived = client.get("/search", params={"q": "Old searchable"})
        archived_result = next(item for item in archived.json() if item["id"] == archived_ticket["id"])
        assert archived_result["archived"] is True


def test_global_search_rejects_empty_query() -> None:
    with TestClient(app) as client:
        response = client.get("/search", params={"q": ""})
        assert response.status_code == 422
