from agentdesk_api.main import app
from fastapi.testclient import TestClient


def test_ticket_git_artifacts_are_provider_neutral_and_audited() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Artifacts"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Ship code"}).json()
        artifact = client.post(f"/tickets/{ticket['id']}/artifacts", json={"kind": "pull_request", "identifier": "42", "title": "Ship code", "url": "https://git.example/review/42", "metadata": {"state": "open", "source_branch": "agent/ad-12"}})
        assert artifact.status_code == 201
        assert artifact.json()["metadata"] == {"state": "open", "source_branch": "agent/ad-12"}

        branch = client.post(f"/tickets/{ticket['id']}/artifacts", json={"kind": "branch", "identifier": "agent/ad-12"})
        commit = client.post(f"/tickets/{ticket['id']}/artifacts", json={"kind": "commit", "identifier": "abc123", "title": "Add artifacts"})
        assert branch.status_code == commit.status_code == 201
        assert len(client.get(f"/tickets/{ticket['id']}/artifacts").json()) == 3

        updated = client.patch(f"/artifacts/{artifact.json()['id']}", json={"metadata": {"state": "merged"}})
        assert updated.status_code == 200
        assert updated.json()["metadata"]["state"] == "merged"
        events = client.get(f"/tickets/{ticket['id']}/events").json()
        assert [event["event_type"] for event in events].count("git_artifact_created") == 3
        assert events[-1]["event_type"] == "git_artifact_updated"
        assert events[-1]["payload"]["changes"] == {
            "metadata": {
                "from": {"state": "open", "source_branch": "agent/ad-12"},
                "to": {"state": "merged"},
            }
        }


def test_git_artifact_repository_must_belong_to_ticket_project() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Ticket project"}).json()
        other_project = client.post("/projects", json={"name": "Other project"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Ship code"}).json()
        repository = client.post(
            f"/projects/{other_project['id']}/repositories",
            json={"name": "other", "remote_url": "https://example.invalid/other.git"},
        ).json()

        response = client.post(
            f"/tickets/{ticket['id']}/artifacts",
            json={"kind": "branch", "identifier": "agent/ad-12", "repository_id": repository["id"]},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Repository must belong to the ticket project"


def test_git_artifact_endpoints_report_missing_records() -> None:
    with TestClient(app) as client:
        assert client.get("/tickets/missing/artifacts").status_code == 404
        assert client.post(
            "/tickets/missing/artifacts",
            json={"kind": "commit", "identifier": "abc123"},
        ).status_code == 404
        assert client.patch("/artifacts/missing", json={"title": "Missing"}).status_code == 404
