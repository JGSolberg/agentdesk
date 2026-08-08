import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from agentdesk_api.agent_models import Agent, AgentRun
from agentdesk_api.database import SessionLocal
from agentdesk_api.main import app
from agentdesk_api.models import Workspace, WorkspaceStatus
from agentdesk_api.services.agent_adapters import CodexCliAdapter


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


def test_agent_run_requires_explicit_override_for_done_ticket() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Run Guard"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Already shipped", "status": "done"}).json()
        agent = client.post(f"/projects/{project['id']}/agents", json={"name": "Reviewer", "provider": "manual"}).json()

        blocked = client.post(f"/tickets/{ticket['id']}/runs", json={"agent_id": agent["id"]})
        assert blocked.status_code == 409
        assert "not normally actionable" in blocked.json()["detail"]

        allowed = client.post(f"/tickets/{ticket['id']}/runs", json={"agent_id": agent["id"], "allow_non_actionable": True})
        assert allowed.status_code == 201
        events = client.get(f"/tickets/{ticket['id']}/events").json()
        created = [event for event in events if event["event_type"] == "agent_run_created"][-1]
        assert created["payload"]["non_actionable_override"] is True


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


def test_codex_adapter_builds_sandboxed_json_exec_plan(tmp_path: Path) -> None:
    adapter = CodexCliAdapter()
    agent = Agent(id="agent-1", project_id="project-1", name="Codex", provider="codex", model="gpt-5.6-sol")
    run = AgentRun(
        id="run-1",
        ticket_id="ticket-1",
        agent_id="agent-1",
        context_snapshot={
            "ticket_key": "AD-42",
            "title": "Provider adapters",
            "type": "story",
            "priority": "high",
            "goal": "Run Codex through a provider adapter",
            "description": "Keep executor provider-neutral",
            "acceptance_criteria": ["Codex can edit the worktree", "Telemetry is captured"],
            "definition_of_done": ["Tests pass"],
            "constraints": ["Do not push"],
            "context": [],
            "relevant_files": ["apps/api"],
        },
    )
    workspace = Workspace(id="workspace-1", project_id="project-1", repository_id="repo-1", ticket_id="ticket-1", name="AD-42", branch="agent/AD-42", path=str(tmp_path), status=WorkspaceStatus.ACTIVE)

    plan = adapter.build_plan(agent, run, workspace)

    assert plan.shell is False
    assert isinstance(plan.command, list)
    assert Path(plan.command[0]).stem.lower() == "codex"
    assert plan.command[1:5] == ["exec", "--approve-for-me", "--json", "--ephemeral"]
    assert "--sandbox" not in plan.command
    assert plan.command[5:7] == ["--model", "gpt-5.6-sol"]
    assert plan.command[-1] == "-"
    assert plan.stdin is not None
    assert "AD-42 — Provider adapters" in plan.stdin
    assert "Do not push, merge, or create a pull request." in plan.stdin
    assert plan.environment["AGENTDESK_TICKET_KEY"] == "AD-42"
    assert Path(plan.environment["TMP"]).is_relative_to(tmp_path)
    assert Path(plan.environment["UV_CACHE_DIR"]).is_relative_to(tmp_path)
    assert Path(plan.environment["TMP"]).is_dir()
    assert Path(plan.environment["UV_CACHE_DIR"]).is_dir()


def test_codex_adapter_parses_jsonl_telemetry_and_final_message() -> None:
    adapter = CodexCliAdapter()
    stdout = "\n".join([
        json.dumps({"type": "thread.started", "thread_id": "thread-123"}),
        json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "uv run pytest", "status": "completed"}}),
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Implemented the adapter and tests pass."}}),
        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 25}}),
    ])

    outcome = adapter.parse_output(stdout, "", 0)

    assert outcome.error is None
    assert outcome.result == "Implemented the adapter and tests pass."
    assert ("codex", "Thread thread-123") in outcome.logs
    assert any(level == "command" and "uv run pytest" in message for level, message in outcome.logs)
    assert any(level == "usage" and "input_tokens" in message for level, message in outcome.logs)
