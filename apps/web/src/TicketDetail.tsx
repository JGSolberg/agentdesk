import { FormEvent, useEffect, useState } from "react";
import { NavLink, useParams } from "react-router-dom";

import { listRepositories, type Repository } from "./api/repositories";
import {
  getTicket,
  listTicketEvents,
  updateTicket,
  type Ticket,
  type TicketEvent,
  type TicketPriority,
  type TicketStatus,
  type TicketType,
} from "./api/tickets";
import { createWorkspace, listWorkspaces, removeWorkspace, type Workspace } from "./api/workspaces";
import TicketLifecycleActions from "./TicketLifecycleActions";
import WorkspaceStatusCard from "./WorkspaceStatusCard";

function LabelList({ items, empty }: { items: string[]; empty: string }) {
  if (items.length === 0) return <p className="detail-empty">{empty}</p>;
  return <ul className="detail-list">{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>;
}

function eventSummary(event: TicketEvent): string {
  if (event.event_type === "ticket_created") return "Ticket created";
  if (event.event_type === "ticket_cancelled") return "Ticket cancelled";
  if (event.event_type === "ticket_reopened") return "Ticket reopened";
  if (event.event_type === "ticket_archived") return "Ticket archived";
  if (event.event_type === "ticket_unarchived") return "Ticket unarchived";
  if (event.event_type === "dependency_added") return `Dependency added: ${String(event.payload.dependency_key ?? "ticket")}`;
  if (event.event_type === "dependency_removed") return `Dependency removed: ${String(event.payload.dependency_key ?? "ticket")}`;
  if (event.event_type === "workspace_created") return `Workspace created: ${String(event.payload.branch ?? event.payload.name ?? "workspace")}`;
  if (event.event_type === "workspace_reactivated") return `Workspace reactivated: ${String(event.payload.branch ?? event.payload.name ?? "workspace")}`;
  if (event.event_type === "workspace_removed") return `Workspace removed: ${String(event.payload.branch ?? event.payload.name ?? "workspace")}`;
  if (event.event_type === "ticket_updated") {
    const changes = event.payload.changes as Record<string, { from?: unknown; to?: unknown }> | undefined;
    if (!changes) return "Ticket updated";
    const entries = Object.entries(changes);
    if (entries.length === 1) {
      const [field, change] = entries[0];
      return `${field.replaceAll("_", " ")}: ${String(change.from ?? "—")} → ${String(change.to ?? "—")}`;
    }
    return `Updated ${entries.map(([field]) => field.replaceAll("_", " ")).join(", ")}`;
  }
  return event.event_type.replaceAll("_", " ");
}

function lines(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

export default function TicketDetail() {
  const { ticketId } = useParams();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [events, setEvents] = useState<TicketEvent[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceRepositoryId, setWorkspaceRepositoryId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [workspaceBusy, setWorkspaceBusy] = useState(false);

  async function loadWorkspaces(projectId: string, currentTicketId: string) {
    const nextRepositories = await listRepositories(projectId);
    setRepositories(nextRepositories);
    setWorkspaceRepositoryId((current) => current || nextRepositories.find((repository) => repository.is_primary)?.id || nextRepositories[0]?.id || "");
    const grouped = await Promise.all(nextRepositories.map((repository) => listWorkspaces(repository.id)));
    setWorkspaces(grouped.flat().filter((workspace) => workspace.ticket_id === currentTicketId));
  }

  async function reload(id: string) {
    const nextTicket = await getTicket(id);
    const [nextEvents] = await Promise.all([
      listTicketEvents(id),
      loadWorkspaces(nextTicket.project_id, id),
    ]);
    setTicket(nextTicket);
    setEvents(nextEvents);
  }

  useEffect(() => {
    if (!ticketId) return;
    setTicket(null);
    setEvents([]);
    setRepositories([]);
    setWorkspaces([]);
    setError(null);
    reload(ticketId).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load ticket"));
  }, [ticketId]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ticketId) return;
    const data = new FormData(event.currentTarget);
    setSaving(true);
    setError(null);
    try {
      await updateTicket(ticketId, {
        title: String(data.get("title") ?? "").trim(), type: String(data.get("type")) as TicketType,
        status: String(data.get("status")) as TicketStatus, priority: String(data.get("priority")) as TicketPriority,
        goal: String(data.get("goal") ?? "").trim() || null, description: String(data.get("description") ?? "").trim() || null,
        acceptance_criteria: lines(String(data.get("acceptance_criteria") ?? "")), definition_of_done: lines(String(data.get("definition_of_done") ?? "")),
        constraints: lines(String(data.get("constraints") ?? "")), context: lines(String(data.get("context") ?? "")),
        relevant_files: lines(String(data.get("relevant_files") ?? "")), estimated_complexity: String(data.get("estimated_complexity") ?? "").trim() || null,
        requires_human: data.get("requires_human") === "on",
      });
      await reload(ticketId); setEditing(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save ticket"); }
    finally { setSaving(false); }
  }

  async function makeWorkspace() {
    if (!ticketId || !workspaceRepositoryId) return;
    setWorkspaceBusy(true); setError(null);
    try { await createWorkspace(workspaceRepositoryId, { ticket_id: ticketId }); await reload(ticketId); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to create workspace"); }
    finally { setWorkspaceBusy(false); }
  }

  async function archiveWorkspace(workspace: Workspace) {
    if (!ticketId) return;
    if (!window.confirm(`Remove worktree ${workspace.branch}? The branch and workspace history will remain.`)) return;
    setWorkspaceBusy(true); setError(null);
    try { await removeWorkspace(workspace.id); await reload(ticketId); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to remove workspace"); }
    finally { setWorkspaceBusy(false); }
  }

  if (error && !ticket) return <section className="page"><div className="notice error-notice"><strong>Unable to load ticket.</strong><span>{error}</span></div></section>;
  if (!ticket) return <section className="page loading-page">Loading ticket…</section>;

  const activeWorkspaces = workspaces.filter((workspace) => workspace.status === "active");
  const archivedWorkspaces = workspaces.filter((workspace) => workspace.status === "removed");
  const cloneReadyRepositories = repositories.filter((repository) => repository.managed_path);

  return (
    <section className="page ticket-detail-page">
      <div className="detail-toolbar"><NavLink className="detail-back" to={`/projects/${ticket.project_id}`}>← Back to board</NavLink><button className="detail-edit-button" type="button" onClick={() => setEditing((value) => !value)}>{editing ? "Cancel" : "Edit ticket"}</button></div>
      <TicketLifecycleActions ticket={ticket} onChanged={() => reload(ticket.id)} />
      {error && <div className="notice error-notice"><strong>Ticket action failed.</strong><span>{error}</span></div>}
      {editing ? (
        <form className="ticket-edit-form" onSubmit={save}>
          <div className="ticket-edit-row ticket-edit-title-row"><label>Title<input name="title" defaultValue={ticket.title} required /></label></div>
          <div className="ticket-edit-row four-up">
            <label>Type<select name="type" defaultValue={ticket.type}>{["epic","story","task","bug","spike"].map((value) => <option key={value}>{value}</option>)}</select></label>
            <label>Status<select name="status" defaultValue={ticket.status}>{["backlog","ready","in_progress","review","done","blocked","needs_human","agent_failed","cancelled"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
            <label>Priority<select name="priority" defaultValue={ticket.priority}>{["low","medium","high","critical"].map((value) => <option key={value}>{value}</option>)}</select></label>
            <label>Complexity<input name="estimated_complexity" defaultValue={ticket.estimated_complexity ?? ""} placeholder="small / medium / large" /></label>
          </div>
          <label>Goal<textarea name="goal" defaultValue={ticket.goal ?? ""} rows={3} /></label>
          <label>Description<textarea name="description" defaultValue={ticket.description ?? ""} rows={6} /></label>
          <div className="ticket-edit-row two-up"><label>Acceptance criteria <span>one per line</span><textarea name="acceptance_criteria" defaultValue={ticket.acceptance_criteria.join("\n")} rows={7} /></label><label>Definition of done <span>one per line</span><textarea name="definition_of_done" defaultValue={ticket.definition_of_done.join("\n")} rows={7} /></label></div>
          <div className="ticket-edit-row two-up"><label>Constraints <span>one per line</span><textarea name="constraints" defaultValue={ticket.constraints.join("\n")} rows={5} /></label><label>Context <span>one per line</span><textarea name="context" defaultValue={ticket.context.join("\n")} rows={5} /></label></div>
          <label>Relevant files <span>one per line</span><textarea name="relevant_files" defaultValue={ticket.relevant_files.join("\n")} rows={4} /></label>
          <label className="ticket-edit-checkbox"><input name="requires_human" type="checkbox" defaultChecked={ticket.requires_human} /> Requires human attention</label>
          <div className="ticket-edit-actions"><button type="button" onClick={() => setEditing(false)}>Cancel</button><button type="submit" disabled={saving}>{saving ? "Saving…" : "Save changes"}</button></div>
        </form>
      ) : (
        <>
          <header className="ticket-detail-header"><div><div className="ticket-detail-kicker"><span>{ticket.ticket_key}</span><span>{ticket.type}</span>{ticket.archived && <span>archived</span>}</div><h1>{ticket.title}</h1></div><div className="ticket-detail-badges"><span className={`priority-pill ${ticket.priority}`}>{ticket.priority}</span><span className={`detail-status status-${ticket.status}`}>{ticket.status.replaceAll("_", " ")}</span></div></header>
          <div className="ticket-detail-grid">
            <main className="ticket-detail-main">
              <section className="detail-section"><h2>Goal</h2><p>{ticket.goal || "No goal provided."}</p></section>
              <section className="detail-section"><h2>Description</h2><p className="detail-description">{ticket.description || "No description provided."}</p></section>
              <section className="detail-section"><h2>Acceptance criteria</h2><LabelList items={ticket.acceptance_criteria} empty="No acceptance criteria yet." /></section>
              <section className="detail-section"><h2>Definition of done</h2><LabelList items={ticket.definition_of_done} empty="No definition of done yet." /></section>
              <section className="detail-section"><h2>Constraints</h2><LabelList items={ticket.constraints} empty="No constraints." /></section>
              <section className="detail-section"><h2>Context</h2><LabelList items={ticket.context} empty="No additional context." /></section>
              <section className="detail-section ticket-workspaces">
                <div className="workspace-heading"><div><h2>Workspaces</h2><p>AgentDesk-owned worktrees associated with this ticket.</p></div></div>
                {activeWorkspaces.length === 0 && <p className="detail-empty">No active workspace.</p>}
                {activeWorkspaces.map((workspace) => {
                  const repository = repositories.find((item) => item.id === workspace.repository_id);
                  return <article className="ticket-workspace-card" key={workspace.id}><div className="ticket-workspace-content"><div className="ticket-workspace-meta"><strong>{workspace.branch}</strong><span>{repository?.name ?? "Repository"}</span><code>{workspace.path}</code></div><WorkspaceStatusCard workspace={workspace} /></div><button type="button" onClick={() => void archiveWorkspace(workspace)} disabled={workspaceBusy}>Remove worktree</button></article>;
                })}
                {activeWorkspaces.length === 0 && cloneReadyRepositories.length > 0 && <div className="ticket-workspace-create"><select value={workspaceRepositoryId} onChange={(event) => setWorkspaceRepositoryId(event.target.value)}>{cloneReadyRepositories.map((repository) => <option key={repository.id} value={repository.id}>{repository.name}</option>)}</select><button type="button" onClick={() => void makeWorkspace()} disabled={workspaceBusy || !workspaceRepositoryId}>{workspaceBusy ? "Creating…" : "Create workspace"}</button></div>}
                {activeWorkspaces.length === 0 && cloneReadyRepositories.length === 0 && repositories.length > 0 && <p className="detail-empty">Clone a project repository before creating a workspace.</p>}
                {repositories.length === 0 && <p className="detail-empty">Register a repository for this project before creating a workspace.</p>}
                {archivedWorkspaces.length > 0 && <details className="archived-workspaces"><summary>{archivedWorkspaces.length} archived workspace{archivedWorkspaces.length === 1 ? "" : "s"}</summary>{archivedWorkspaces.map((workspace) => <div key={workspace.id}><code>{workspace.branch}</code><span>{workspace.path}</span></div>)}</details>}
              </section>
            </main>
            <aside className="ticket-detail-aside"><section className="detail-panel"><span>Priority</span><strong>{ticket.priority}</strong></section><section className="detail-panel"><span>Complexity</span><strong>{ticket.estimated_complexity || "—"}</strong></section><section className="detail-panel"><span>Parent</span><strong>{ticket.parent_id || "—"}</strong></section><section className="detail-panel"><span>Dependencies</span><strong>{ticket.dependency_ids.length || "None"}</strong>{ticket.dependency_ids.map((id) => <code key={id}>{id}</code>)}</section><section className="detail-panel"><span>Blocked by</span><strong>{ticket.blocked_by_ids.length || "None"}</strong></section><section className="detail-panel"><span>Human required</span><strong>{ticket.requires_human ? "Yes" : "No"}</strong></section><section className="detail-panel"><span>Relevant files</span>{ticket.relevant_files.length === 0 && <strong>None</strong>}{ticket.relevant_files.map((file) => <code key={file}>{file}</code>)}</section></aside>
          </div>
        </>
      )}
      <section className="detail-section detail-activity"><h2>Activity</h2>{events.length === 0 && <p className="detail-empty">No recorded activity yet.</p>}<div className="activity-timeline">{[...events].reverse().map((event) => <article className="activity-event" key={event.id}><span className="activity-dot" /><div><strong>{eventSummary(event)}</strong><p>{event.actor} · {new Date(event.created_at).toLocaleString()}</p></div></article>)}</div></section>
    </section>
  );
}
