import sys
from pathlib import Path

from fastapi.testclient import TestClient

from agentdesk_api.database import SessionLocal
from agentdesk_api.main import app
from agentdesk_api.models import Workspace, WorkspaceStatus


def test_agent_run_lifecycle_and_context_snapshot() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Agent Runtime"}).json()
        ticket_response = client.post(f"/projects/{project['id']}/tickets", json={"title": "Implement executor", "goal": "Run a coding agent safely", "acceptance_criteria": ["Run is isolated", "Result is reviewable"], "priority": "high"})
        assert ticket_response.status_code == 201
        ticket = ticket_response.json()
        agent_response = client.post(f"/projects/{project['id']}/agents", json={"name": "Manual test agent", "provider": "manual", "capabilities": ["code", "test"]})
        assert agent_response.status_code == 201
        agent = agent_response.json()
        run_response = client.post(f"/tickets/{ticket['id']}/runs", json={"agent_id": agent["id"]})
        assert run_response.status_code == 201
        run = run_response.json()
        assert run["status"] == "queued"
        assert run["context_snapshot"]["ticket_key"] == ticket["ticket_key"]
        assert run["context_snapshot"]["goal"] == "Run a coding agent safely"
        assert run["context_snapshot"]["acceptance_criteria"] == ["Run is isolated", "Result is reviewable"]
        assert client.patch(f"/tickets/{ticket['id']}", json={"goal": "Changed later"}).status_code == 200
        listed = client.get(f"/tickets/{ticket['id']}/runs")
        assert listed.status_code == 200
        assert listed.json()[0]["context_snapshot"]["goal"] == "Run a coding agent safely"
        running = client.patch(f"/runs/{run['id']}", json={"status": "running"})
        assert running.status_code == 200
        assert running.json()["started_at"] is not None
        logged = client.post(f"/runs/{run['id']}/logs", json={"level": "info", "message": "Inspecting repository"})
        assert logged.status_code == 200
        assert logged.json()["logs"][-1]["message"] == "Inspecting repository"
        completed = client.patch(f"/runs/{run['id']}", json={"status": "succeeded", "result": "Implemented and tested"})
        assert completed.status_code == 200
        assert completed.json()["result"] == "Implemented and tested"
        assert completed.json()["finished_at"] is not None
        events = client.get(f"/tickets/{ticket['id']}/events").json()
        assert any(event["event_type"] == "agent_run_created" for event in events)
        assert any(event["event_type"] == "agent_run_updated" for event in events)


def test_agent_and_ticket_must_share_project() -> None:
    with TestClient(app) as client:
        project_a = client.post("/projects", json={"name": "Alpha"}).json()
        project_b = client.post("/projects", json={"name": "Beta"}).json()
        ticket = client.post(f"/projects/{project_a['id']}/tickets", json={"title": "Alpha work"}).json()
        agent = client.post(f"/projects/{project_b['id']}/agents", json={"name": "Beta agent"}).json()
        response = client.post(f"/tickets/{ticket['id']}/runs", json={"agent_id": agent["id"]})
        assert response.status_code == 400


def test_local_command_executor_uses_workspace_and_ticket_context(tmp_path: Path) -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Executor"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Execute locally"}).json()
        repository = client.post(f"/projects/{project['id']}/repositories", json={"name": "repo", "remote_url": "https://example.invalid/repo.git"}).json()

        with SessionLocal() as db:
            workspace = Workspace(project_id=project["id"], repository_id=repository["id"], ticket_id=ticket["id"], name="executor-test", branch="agent/executor-test", path=str(tmp_path), status=WorkspaceStatus.ACTIVE)
            db.add(workspace)
            db.commit()
            db.refresh(workspace)
            workspace_id = workspace.id

        command = f'"{sys.executable}" -c "import os; print(os.environ[\'AGENTDESK_TICKET_KEY\'])"'
        agent = client.post(f"/projects/{project['id']}/agents", json={"name": "Python echo", "provider": "local", "command": command}).json()
        run = client.post(f"/tickets/{ticket['id']}/runs", json={"agent_id": agent["id"], "workspace_id": workspace_id}).json()
        executed = client.post(f"/runs/{run['id']}/execute")
        assert executed.status_code == 200
        body = executed.json()
        assert body["status"] == "succeeded"
        assert ticket["ticket_key"] in body["result"]
        assert body["started_at"] is not None
        assert body["finished_at"] is not None
        assert any(entry["level"] == "stdout" and ticket["ticket_key"] in entry["message"] for entry in body["logs"])
