from fastapi.testclient import TestClient

from agentdesk_api.main import app


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
