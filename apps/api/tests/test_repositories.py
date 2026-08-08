from fastapi.testclient import TestClient

from agentdesk_api.main import app


def test_repository_crud_and_primary_selection() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Repo Project"}).json()

        first_response = client.post(
            f"/projects/{project['id']}/repositories",
            json={
                "name": "agentdesk",
                "local_path": r"E:\\Coding\\agentdesk",
                "provider": "github",
                "remote_url": "https://github.com/JGSolberg/agentdesk",
                "default_branch": "main",
            },
        )
        assert first_response.status_code == 201
        first = first_response.json()
        assert first["is_primary"] is True

        second_response = client.post(
            f"/projects/{project['id']}/repositories",
            json={"name": "docs", "local_path": r"E:\\Coding\\docs", "is_primary": True},
        )
        assert second_response.status_code == 201
        second = second_response.json()
        assert second["is_primary"] is True

        listed = client.get(f"/projects/{project['id']}/repositories")
        assert listed.status_code == 200
        repositories = listed.json()
        assert len(repositories) == 2
        assert repositories[0]["id"] == second["id"]
        assert repositories[0]["is_primary"] is True
        assert next(repo for repo in repositories if repo["id"] == first["id"])["is_primary"] is False

        updated = client.patch(
            f"/repositories/{first['id']}",
            json={"default_branch": "develop", "is_primary": True},
        )
        assert updated.status_code == 200
        assert updated.json()["default_branch"] == "develop"
        assert updated.json()["is_primary"] is True

        deleted = client.delete(f"/repositories/{first['id']}")
        assert deleted.status_code == 204

        remaining = client.get(f"/projects/{project['id']}/repositories").json()
        assert len(remaining) == 1
        assert remaining[0]["id"] == second["id"]
        assert remaining[0]["is_primary"] is True


def test_repository_requires_project() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/projects/missing/repositories",
            json={"name": "missing", "local_path": r"E:\\missing"},
        )
        assert response.status_code == 404
