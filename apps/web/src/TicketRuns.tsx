import { FormEvent, useEffect, useState } from "react";

import { createAgent, createRun, executeRun, listAgents, listRuns, type Agent, type AgentRun } from "./api/agents";
import type { TicketStatus, TicketType } from "./api/tickets";
import type { Workspace } from "./api/workspaces";

type Props = {
  projectId: string;
  ticketId: string;
  ticketType: TicketType;
  ticketStatus: TicketStatus;
  archived: boolean;
  workspaces: Workspace[];
  onChanged?: () => Promise<void> | void;
};

function downloadRunLog(run: AgentRun, agent?: Agent) {
  const header = [
    `AgentDesk run ${run.id}`,
    `Agent: ${agent?.name ?? run.agent_id}`,
    `Provider: ${agent?.provider ?? "unknown"}`,
    `Status: ${run.status}`,
    `Created: ${run.created_at}`,
    run.started_at ? `Started: ${run.started_at}` : null,
    run.finished_at ? `Finished: ${run.finished_at}` : null,
    "",
    run.result ? `RESULT\n${run.result}` : null,
    run.error ? `ERROR\n${run.error}` : null,
    "",
    "LOGS",
  ].filter((line): line is string => line !== null);
  const logLines = run.logs.flatMap((entry) => [`[${entry.timestamp}] ${entry.level}`, entry.message, ""]);
  const blob = new Blob([[...header, ...logLines].join("\n")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const safeAgent = (agent?.name ?? "agent").replace(/[^a-z0-9_-]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();
  anchor.href = url;
  anchor.download = `agentdesk-${safeAgent || "agent"}-${run.created_at.replace(/[:.]/g, "-")}.log.txt`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function TicketRuns({ projectId, ticketId, ticketType, ticketStatus, archived, workspaces, onChanged }: Props) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [agentId, setAgentId] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [newProvider, setNewProvider] = useState<"codex" | "local">("codex");
  const [allowNonActionable, setAllowNonActionable] = useState(false);

  async function reload() {
    const [nextAgents, nextRuns] = await Promise.all([listAgents(projectId), listRuns(ticketId)]);
    setAgents(nextAgents);
    setRuns(nextRuns);
    setAgentId((current) => current || nextAgents.find((agent) => agent.enabled)?.id || "");
  }

  useEffect(() => { void reload().catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load agent runs")); }, [projectId, ticketId]);
  useEffect(() => { setWorkspaceId((current) => current || workspaces.find((workspace) => workspace.status === "active")?.id || ""); }, [workspaces]);

  const nonActionableReasons = [
    archived ? "archived" : null,
    ticketType === "epic" ? "epic" : null,
    ticketStatus === "done" || ticketStatus === "cancelled" ? ticketStatus : null,
  ].filter(Boolean) as string[];
  const nonActionable = nonActionableReasons.length > 0;

  async function runAgent() {
    if (!agentId || !workspaceId) return;
    setBusy(true); setError(null);
    try {
      const run = await createRun(ticketId, { agent_id: agentId, workspace_id: workspaceId, allow_non_actionable: nonActionable && allowNonActionable });
      setRuns((items) => [run, ...items]);
      const completed = await executeRun(run.id);
      setRuns((items) => items.map((item) => item.id === completed.id ? completed : item));
      await onChanged?.();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Agent run failed"); }
    finally { setBusy(false); }
  }

  async function addAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name") ?? "").trim();
    const model = String(data.get("model") ?? "").trim();
    const command = String(data.get("command") ?? "").trim();
    if (!name || (newProvider === "local" && !command)) return;
    setBusy(true); setError(null);
    try {
      const agent = await createAgent(projectId, {
        name,
        provider: newProvider,
        model: newProvider === "codex" ? model || null : null,
        command: newProvider === "local" ? command : null,
        capabilities: newProvider === "codex" ? ["workspace", "code", "test"] : ["workspace", "shell"],
      });
      setAgents((items) => [...items, agent]); setAgentId(agent.id); setShowAgentForm(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to create agent"); }
    finally { setBusy(false); }
  }

  const activeWorkspaces = workspaces.filter((workspace) => workspace.status === "active");
  const selectedAgent = agents.find((agent) => agent.id === agentId);
  const runDisabled = busy || !agentId || !workspaceId || (nonActionable && !allowNonActionable);

  return <section className="detail-section ticket-runs">
    <div className="ticket-runs-heading"><div><h2>Agent runs</h2><p>Human-triggered execution in this ticket's isolated workspace.</p></div><button type="button" onClick={() => setShowAgentForm((value) => !value)}>{showAgentForm ? "Close" : "+ Agent"}</button></div>
    {showAgentForm && <form className="ticket-agent-form" onSubmit={addAgent}>
      <input name="name" placeholder="Agent name" required />
      <select value={newProvider} onChange={(event) => setNewProvider(event.target.value as "codex" | "local")}><option value="codex">Codex CLI</option><option value="local">Local command</option></select>
      {newProvider === "codex" ? <><input name="model" placeholder="Model override (optional)" /><span className="ticket-agent-hint">Uses your installed and authenticated Codex CLI with automatic workspace approval.</span></> : <input name="command" placeholder='Command, e.g. python -c "print(\"hello\")"' required />}
      <button disabled={busy} type="submit">Add agent</button>
    </form>}
    <div className="ticket-run-controls">
      <select value={agentId} onChange={(event) => setAgentId(event.target.value)}><option value="">Select agent…</option>{agents.filter((agent) => agent.enabled).map((agent) => <option key={agent.id} value={agent.id}>{agent.name} · {agent.provider}{agent.model ? ` · ${agent.model}` : ""}</option>)}</select>
      <select value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}><option value="">Select workspace…</option>{activeWorkspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.branch}</option>)}</select>
      <button type="button" disabled={runDisabled} onClick={() => void runAgent()}>{busy ? "Running…" : selectedAgent?.provider === "codex" ? "Run Codex" : "Run agent"}</button>
    </div>
    {nonActionable && <div className="ticket-run-override"><strong>This ticket is not normally actionable ({nonActionableReasons.join(", ")}).</strong><label><input type="checkbox" checked={allowNonActionable} onChange={(event) => setAllowNonActionable(event.target.checked)} /> Run anyway</label></div>}
    {selectedAgent?.provider === "codex" && <p className="ticket-agent-hint">Codex receives the ticket goal, description, criteria, constraints, context, and relevant files, then leaves its edits in this worktree for review.</p>}
    {activeWorkspaces.length === 0 && <p className="detail-empty">Create an active workspace before running an agent.</p>}
    {error && <p className="ticket-lifecycle-error">{error}</p>}
    <div className="ticket-run-list">{runs.map((run) => { const agent = agents.find((item) => item.id === run.agent_id); return <details className={`ticket-run-card run-${run.status}`} key={run.id}><summary><div><strong>{agent?.name ?? "Agent"}</strong><span>{agent?.provider ?? "agent"} · {new Date(run.created_at).toLocaleString()}</span></div><div className="ticket-run-summary-actions"><b>{run.status.replaceAll("_", " ")}</b><button type="button" onClick={(event) => { event.preventDefault(); event.stopPropagation(); downloadRunLog(run, agent); }}>Download logs</button></div></summary><div className="ticket-run-body">{run.error && <p className="ticket-lifecycle-error">{run.error}</p>}{run.result && <pre>{run.result}</pre>}{run.logs.length > 0 && <div className="ticket-run-logs">{run.logs.map((entry, index) => <div key={`${entry.timestamp}-${index}`}><span>{entry.level}</span><pre>{entry.message}</pre></div>)}</div>}</div></details>; })}{runs.length === 0 && <p className="detail-empty">No agent runs yet.</p>}</div>
  </section>;
}
