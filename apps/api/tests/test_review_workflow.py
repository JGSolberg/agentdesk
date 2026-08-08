import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from agentdesk_api.database import SessionLocal
from agentdesk_api.main import app
from agentdesk_api.models import Workspace, WorkspaceStatus
from agentdesk_api.services import review_service


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)


def _init_repo(path: Path) -> None:
    _git(path, "init")
    _git(path, "config", "user.email", "agentdesk-test@example.invalid")
    _git(path, "config", "user.name", "AgentDesk Test")
    (path / ".gitignore").write_text(".agentdesk/\n", encoding="utf-8")
    (path / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(path, "add", ".gitignore", "README.md")
    _git(path, "commit", "-m", "baseline")


def test_review_ignores_agentdesk_runtime_files(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    project_id = "project-review"
    repository_id = "repo-review"
    ticket_id = "ticket-review"
    workspace_id = "workspace-review"

    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Review Test"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Review changes"}).json()
        repository = client.post(f"/projects/{project['id']}/repositories", json={"name": "repo", "remote_url": "https://example.invalid/repo.git"}).json()
        project_id, repository_id, ticket_id = project["id"], repository["id"], ticket["id"]

    with SessionLocal() as db:
        workspace = Workspace(id=workspace_id, project_id=project_id, repository_id=repository_id, ticket_id=ticket_id, name="review", branch="agent/review", path=str(tmp_path), status=WorkspaceStatus.ACTIVE)
        db.add(workspace)
        db.commit()

        runtime = tmp_path / ".agentdesk" / "cache"
        runtime.mkdir(parents=True)
        (runtime / "tool.tmp").write_text("runtime", encoding="utf-8")
        assert review_service.workspace_review(db, workspace_id).clean is True

        (tmp_path / "feature.txt").write_text("implemented\n", encoding="utf-8")
        review = review_service.workspace_review(db, workspace_id)
        assert review.clean is False
        assert any(item.path == "feature.txt" for item in review.files)
        assert "feature.txt" in review.diff
        assert "implemented" in review.diff


def test_publish_staging_does_not_name_ignored_agentdesk_path(tmp_path: Path, monkeypatch) -> None:
    _init_repo(tmp_path)
    calls: list[list[str]] = []
    original_run = review_service._run

    def recording_run(args: list[str], *, cwd: Path, allow_failure: bool = False):
        calls.append(args)
        if args[:3] == ["gh", "pr", "view"]:
            return subprocess.CompletedProcess(args, 1, "", "")
        if args[:3] == ["git", "push", "-u"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["gh", "pr", "create"]:
            return subprocess.CompletedProcess(args, 0, "https://github.com/example/repo/pull/1\n", "")
        return original_run(args, cwd=cwd, allow_failure=allow_failure)

    monkeypatch.setattr(review_service, "_run", recording_run)

    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Publish Test"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Publish safely"}).json()
        repository = client.post(f"/projects/{project['id']}/repositories", json={"name": "repo", "remote_url": "https://github.com/example/repo.git"}).json()

        with SessionLocal() as db:
            workspace = Workspace(project_id=project["id"], repository_id=repository["id"], ticket_id=ticket["id"], name="publish", branch="agent/publish", path=str(tmp_path), status=WorkspaceStatus.ACTIVE)
            db.add(workspace)
            db.commit()
            db.refresh(workspace)
            workspace_id = workspace.id

        runtime = tmp_path / ".agentdesk" / "cache"
        runtime.mkdir(parents=True)
        (runtime / "tool.tmp").write_text("runtime", encoding="utf-8")
        (tmp_path / "feature.txt").write_text("implemented\n", encoding="utf-8")

        response = client.post(f"/workspaces/{workspace_id}/publish")
        assert response.status_code == 200

    add_calls = [args for args in calls if args[:2] == ["git", "add"]]
    assert add_calls == [["git", "add", "-A", "--", "."]]
    staged = subprocess.run(["git", "show", "--name-only", "--format="], cwd=tmp_path, check=True, capture_output=True, text=True).stdout
    assert "feature.txt" in staged
    assert ".agentdesk" not in staged


def test_agent_file_change_moves_ticket_to_review(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Agent Review Transition"}).json()
        ticket = client.post(f"/projects/{project['id']}/tickets", json={"title": "Write a file", "status": "ready"}).json()
        repository = client.post(f"/projects/{project['id']}/repositories", json={"name": "repo", "remote_url": "https://example.invalid/repo.git"}).json()

        with SessionLocal() as db:
            workspace = Workspace(project_id=project["id"], repository_id=repository["id"], ticket_id=ticket["id"], name="agent-review", branch="agent/review-transition", path=str(tmp_path), status=WorkspaceStatus.ACTIVE)
            db.add(workspace)
            db.commit()
            db.refresh(workspace)
            workspace_id = workspace.id

        command = f'"{sys.executable}" -c "from pathlib import Path; Path(\'agent-change.txt\').write_text(\'done\\n\')"'
        agent = client.post(f"/projects/{project['id']}/agents", json={"name": "Writer", "provider": "local", "command": command}).json()
        run = client.post(f"/tickets/{ticket['id']}/runs", json={"agent_id": agent["id"], "workspace_id": workspace_id}).json()
        executed = client.post(f"/runs/{run['id']}/execute")

        assert executed.status_code == 200
        assert executed.json()["status"] == "succeeded"
        updated_ticket = client.get(f"/tickets/{ticket['id']}").json()
        assert updated_ticket["status"] == "review"
