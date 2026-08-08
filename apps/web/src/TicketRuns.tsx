import { FormEvent, useEffect, useState } from "react";

import { createAgent, createRun, executeRun, listAgents, listRuns, type Agent, type AgentRun } from "./api/agents";
import type { Workspace } from "./api/workspaces";

export default function TicketRuns({ projectId, ticketId, workspaces }: { projectId: string; ticketId: string; workspaces: Workspace[] }) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [agentId, setAgentId] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAgentForm, setShowAgentForm] = useState(false);

  async function reload() {
    const [nextAgents, nextRuns] = await Promise.all([listAgents(projectId), listRuns(ticketId)]);
    setAgents(nextAgents);
    setRuns(nextRuns);
    setAgentId((current) => current || nextAgents.find((agent) => agent.enabled)?.id || "");
  }

  useEffect(() => { void reload().catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load agent runs")); }, [projectId, ticketId]);
  useEffect(() => { setWorkspaceId((current) => current || workspaces.find((workspace) => workspace.status === "active")?.id || ""); }, [workspaces]);

  async function runAgent() {
    if (!agentId || !workspaceId) return;
    setBusy(true); setError(null);
    try {
      const run = await createRun(ticketId, { agent_id: agentId, workspace_id: workspaceId });
      setRuns((items) => [run, ...items]);
      const completed = await executeRun(run.id);
      setRuns((items) => items.map((item) => item.id === completed.id ? completed : item));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Agent run failed"); }
    finally { setBusy(false); }
  }

  async function addAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name") ?? "").trim();
    const command = String(data.get("command") ?? "").trim();
    if (!name || !command) return;
    setBusy(true); setError(null);
    try {
      const agent = await createAgent(projectId, { name, provider: "local", command, capabilities: ["workspace", "shell"] });
      setAgents((items) => [...items, agent]); setAgentId(agent.id); setShowAgentForm(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to create agent"); }
    finally { setBusy(false); }
  }

  const activeWorkspaces = workspaces.filter((workspace) => workspace.status === "active");

  return <section className="detail-section ticket-runs">
    <div className="ticket-runs-heading"><div><h2>Agent runs</h2><p>Human-triggered execution in this ticket's isolated workspace.</p></div><button type="button" onClick={() => setShowAgentForm((value) => !value)}>{showAgentForm ? "Close" : "+ Local agent"}</button></div>
    {showAgentForm && <form className="ticket-agent-form" onSubmit={addAgent}><input name="name" placeholder="Agent name" required /><input name="command" placeholder='Command, e.g. python -c "print(\"hello\")"' required /><button disabled={busy} type="submit">Add agent</button></form>}
    <div className="ticket-run-controls">
      <select value={agentId} onChange={(event) => setAgentId(event.target.value)}><option value="">Select agent…</option>{agents.filter((agent) => agent.enabled).map((agent) => <option key={agent.id} value={agent.id}>{agent.name} · {agent.provider}</option>)}</select>
      <select value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}><option value="">Select workspace…</option>{activeWorkspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.branch}</option>)}</select>
      <button type="button" disabled={busy || !agentId || !workspaceId} onClick={() => void runAgent()}>{busy ? "Running…" : "Run agent"}</button>
    </div>
    {activeWorkspaces.length === 0 && <p className="detail-empty">Create an active workspace before running a local agent.</p>}
    {error && <p className="ticket-lifecycle-error">{error}</p>}
    <div className="ticket-run-list">{runs.map((run) => { const agent = agents.find((item) => item.id === run.agent_id); return <details className={`ticket-run-card run-${run.status}`} key={run.id}><summary><div><strong>{agent?.name ?? "Agent"}</strong><span>{new Date(run.created_at).toLocaleString()}</span></div><b>{run.status.replaceAll("_", " ")}</b></summary><div className="ticket-run-body">{run.error && <p className="ticket-lifecycle-error">{run.error}</p>}{run.result && <pre>{run.result}</pre>}{run.logs.length > 0 && <div className="ticket-run-logs">{run.logs.map((entry, index) => <div key={`${entry.timestamp}-${index}`}><span>{entry.level}</span><pre>{entry.message}</pre></div>)}</div>}</div></details>; })}{runs.length === 0 && <p className="detail-empty">No agent runs yet.</p>}</div>
  </section>;
}
