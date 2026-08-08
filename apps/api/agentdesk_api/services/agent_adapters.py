from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
from typing import Protocol

from ..agent_models import Agent, AgentRun
from ..models import Workspace


@dataclass(frozen=True)
class ExecutionPlan:
    command: str | list[str]
    shell: bool
    environment: dict[str, str]


@dataclass(frozen=True)
class ExecutionOutcome:
    logs: list[tuple[str, str]]
    result: str | None
    error: str | None


class AgentAdapter(Protocol):
    provider: str

    def build_plan(self, agent: Agent, run: AgentRun, workspace: Workspace) -> ExecutionPlan: ...

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> ExecutionOutcome: ...


def _agentdesk_environment(run: AgentRun, workspace: Workspace) -> dict[str, str]:
    return {
        "AGENTDESK_RUN_ID": run.id,
        "AGENTDESK_TICKET_ID": run.ticket_id,
        "AGENTDESK_TICKET_KEY": str(run.context_snapshot.get("ticket_key", "")),
        "AGENTDESK_WORKSPACE": workspace.path,
        "AGENTDESK_TICKET_CONTEXT_JSON": json.dumps(run.context_snapshot),
    }


class LocalCommandAdapter:
    provider = "local"

    def build_plan(self, agent: Agent, run: AgentRun, workspace: Workspace) -> ExecutionPlan:
        if not agent.command:
            raise ValueError("Local command agent has no command configured")
        return ExecutionPlan(command=agent.command, shell=True, environment=_agentdesk_environment(run, workspace))

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> ExecutionOutcome:
        logs: list[tuple[str, str]] = []
        if stdout.strip():
            logs.append(("stdout", stdout.rstrip()))
        if stderr.strip():
            logs.append(("stderr", stderr.rstrip()))
        if returncode == 0:
            return ExecutionOutcome(logs=logs, result=stdout.rstrip() or "Command completed successfully", error=None)
        return ExecutionOutcome(logs=logs, result=stdout.rstrip() or None, error=f"Agent command exited with code {returncode}")


class CodexCliAdapter:
    provider = "codex"

    def build_plan(self, agent: Agent, run: AgentRun, workspace: Workspace) -> ExecutionPlan:
        executable = shutil.which("codex") or "codex"
        command = [executable, "exec", "--sandbox", "workspace-write", "--json", "--ephemeral"]
        if agent.model:
            command.extend(["--model", agent.model])
        command.append(_codex_prompt(run.context_snapshot))
        return ExecutionPlan(command=command, shell=False, environment=_agentdesk_environment(run, workspace))

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> ExecutionOutcome:
        logs: list[tuple[str, str]] = []
        final_message: str | None = None
        parse_errors = 0

        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                logs.append(("codex", line))
                continue

            event_type = str(event.get("type", "codex"))
            item = event.get("item") if isinstance(event.get("item"), dict) else None
            if item:
                item_type = str(item.get("type", "item"))
                if item_type == "agent_message" and item.get("text"):
                    final_message = str(item["text"])
                    logs.append(("agent", final_message))
                elif item_type == "command_execution":
                    command = item.get("command", "command")
                    status = item.get("status", "")
                    logs.append(("command", f"{command} [{status}]".rstrip()))
                elif item_type in {"file_change", "file_changes"}:
                    logs.append(("file", json.dumps(item, ensure_ascii=False)))
                elif item_type == "mcp_tool_call":
                    logs.append(("tool", json.dumps(item, ensure_ascii=False)))
                elif item_type == "web_search":
                    logs.append(("web", json.dumps(item, ensure_ascii=False)))
                elif item_type == "plan_update":
                    logs.append(("plan", json.dumps(item, ensure_ascii=False)))
            elif event_type == "thread.started":
                logs.append(("codex", f"Thread {event.get('thread_id', 'started')}"))
            elif event_type == "turn.completed":
                usage = event.get("usage")
                if usage:
                    logs.append(("usage", json.dumps(usage, ensure_ascii=False)))
            elif event_type in {"turn.failed", "error"}:
                logs.append(("error", json.dumps(event, ensure_ascii=False)))

        if stderr.strip():
            logs.append(("stderr", stderr.rstrip()))
        if parse_errors:
            logs.append(("codex", f"{parse_errors} non-JSON Codex output line(s) captured verbatim"))

        if returncode == 0:
            return ExecutionOutcome(logs=logs, result=final_message or "Codex completed successfully", error=None)
        return ExecutionOutcome(logs=logs, result=final_message, error=f"Codex exited with code {returncode}")


def _codex_prompt(context: dict) -> str:
    def bullets(values: object) -> str:
        if not isinstance(values, list) or not values:
            return "- None"
        return "\n".join(f"- {value}" for value in values)

    return f"""You are implementing an AgentDesk ticket in an isolated Git worktree.

Ticket: {context.get('ticket_key', '')} — {context.get('title', '')}
Type: {context.get('type', '')}
Priority: {context.get('priority', '')}

Goal:
{context.get('goal') or 'No explicit goal provided.'}

Description:
{context.get('description') or 'No description provided.'}

Acceptance criteria:
{bullets(context.get('acceptance_criteria'))}

Definition of done:
{bullets(context.get('definition_of_done'))}

Constraints:
{bullets(context.get('constraints'))}

Context:
{bullets(context.get('context'))}

Relevant files:
{bullets(context.get('relevant_files'))}

Instructions:
- Work only on this ticket in the current worktree.
- Inspect the repository and follow project instructions such as AGENTS.md.
- Make the smallest coherent implementation that satisfies the ticket.
- Run relevant tests, linters, or builds when practical.
- Do not push, merge, or create a pull request.
- Do not create or switch branches; AgentDesk owns the worktree and branch.
- Leave all resulting changes in the worktree for human review.
- Finish with a concise summary of changes, validation performed, and anything that still needs human attention.
"""


_ADAPTERS: dict[str, AgentAdapter] = {
    "local": LocalCommandAdapter(),
    "command": LocalCommandAdapter(),
    "codex": CodexCliAdapter(),
}


def get_adapter(provider: str) -> AgentAdapter | None:
    return _ADAPTERS.get(provider.lower())
