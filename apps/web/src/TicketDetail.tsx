import { FormEvent, useEffect, useState } from "react";
import { NavLink, useParams } from "react-router-dom";

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

function LabelList({ items, empty }: { items: string[]; empty: string }) {
  if (items.length === 0) return <p className="detail-empty">{empty}</p>;
  return <ul className="detail-list">{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>;
}

function eventSummary(event: TicketEvent): string {
  if (event.event_type === "ticket_created") return "Ticket created";
  if (event.event_type === "dependency_added") return `Dependency added: ${String(event.payload.dependency_key ?? "ticket")}`;
  if (event.event_type === "dependency_removed") return `Dependency removed: ${String(event.payload.dependency_key ?? "ticket")}`;
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
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  async function reload(id: string) {
    const [nextTicket, nextEvents] = await Promise.all([getTicket(id), listTicketEvents(id)]);
    setTicket(nextTicket);
    setEvents(nextEvents);
  }

  useEffect(() => {
    if (!ticketId) return;
    setTicket(null);
    setEvents([]);
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
        title: String(data.get("title") ?? "").trim(),
        type: String(data.get("type")) as TicketType,
        status: String(data.get("status")) as TicketStatus,
        priority: String(data.get("priority")) as TicketPriority,
        goal: String(data.get("goal") ?? "").trim() || null,
        description: String(data.get("description") ?? "").trim() || null,
        acceptance_criteria: lines(String(data.get("acceptance_criteria") ?? "")),
        definition_of_done: lines(String(data.get("definition_of_done") ?? "")),
        constraints: lines(String(data.get("constraints") ?? "")),
        context: lines(String(data.get("context") ?? "")),
        relevant_files: lines(String(data.get("relevant_files") ?? "")),
        estimated_complexity: String(data.get("estimated_complexity") ?? "").trim() || null,
        requires_human: data.get("requires_human") === "on",
      });
      await reload(ticketId);
      setEditing(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save ticket");
    } finally {
      setSaving(false);
    }
  }

  if (error && !ticket) {
    return <section className="page"><div className="notice error-notice"><strong>Unable to load ticket.</strong><span>{error}</span></div></section>;
  }
  if (!ticket) return <section className="page loading-page">Loading ticket…</section>;

  return (
    <section className="page ticket-detail-page">
      <div className="detail-toolbar">
        <NavLink className="detail-back" to={`/projects/${ticket.project_id}`}>← Back to board</NavLink>
        <button className="detail-edit-button" type="button" onClick={() => setEditing((value) => !value)}>{editing ? "Cancel" : "Edit ticket"}</button>
      </div>

      {error && <div className="notice error-notice"><strong>Ticket action failed.</strong><span>{error}</span></div>}

      {editing ? (
        <form className="ticket-edit-form" onSubmit={save}>
          <div className="ticket-edit-row ticket-edit-title-row">
            <label>Title<input name="title" defaultValue={ticket.title} required /></label>
          </div>
          <div className="ticket-edit-row four-up">
            <label>Type<select name="type" defaultValue={ticket.type}>{["epic","story","task","bug","spike"].map((value) => <option key={value}>{value}</option>)}</select></label>
            <label>Status<select name="status" defaultValue={ticket.status}>{["backlog","ready","in_progress","review","done","blocked","needs_human","agent_failed"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
            <label>Priority<select name="priority" defaultValue={ticket.priority}>{["low","medium","high","critical"].map((value) => <option key={value}>{value}</option>)}</select></label>
            <label>Complexity<input name="estimated_complexity" defaultValue={ticket.estimated_complexity ?? ""} placeholder="small / medium / large" /></label>
          </div>
          <label>Goal<textarea name="goal" defaultValue={ticket.goal ?? ""} rows={3} /></label>
          <label>Description<textarea name="description" defaultValue={ticket.description ?? ""} rows={6} /></label>
          <div className="ticket-edit-row two-up">
            <label>Acceptance criteria <span>one per line</span><textarea name="acceptance_criteria" defaultValue={ticket.acceptance_criteria.join("\n")} rows={7} /></label>
            <label>Definition of done <span>one per line</span><textarea name="definition_of_done" defaultValue={ticket.definition_of_done.join("\n")} rows={7} /></label>
          </div>
          <div className="ticket-edit-row two-up">
            <label>Constraints <span>one per line</span><textarea name="constraints" defaultValue={ticket.constraints.join("\n")} rows={5} /></label>
            <label>Context <span>one per line</span><textarea name="context" defaultValue={ticket.context.join("\n")} rows={5} /></label>
          </div>
          <label>Relevant files <span>one per line</span><textarea name="relevant_files" defaultValue={ticket.relevant_files.join("\n")} rows={4} /></label>
          <label className="ticket-edit-checkbox"><input name="requires_human" type="checkbox" defaultChecked={ticket.requires_human} /> Requires human attention</label>
          <div className="ticket-edit-actions"><button type="button" onClick={() => setEditing(false)}>Cancel</button><button type="submit" disabled={saving}>{saving ? "Saving…" : "Save changes"}</button></div>
        </form>
      ) : (
        <>
          <header className="ticket-detail-header">
            <div><div className="ticket-detail-kicker"><span>{ticket.ticket_key}</span><span>{ticket.type}</span></div><h1>{ticket.title}</h1></div>
            <div className="ticket-detail-badges"><span className={`priority-pill ${ticket.priority}`}>{ticket.priority}</span><span className={`detail-status status-${ticket.status}`}>{ticket.status.replaceAll("_", " ")}</span></div>
          </header>
          <div className="ticket-detail-grid">
            <main className="ticket-detail-main">
              <section className="detail-section"><h2>Goal</h2><p>{ticket.goal || "No goal provided."}</p></section>
              <section className="detail-section"><h2>Description</h2><p className="detail-description">{ticket.description || "No description provided."}</p></section>
              <section className="detail-section"><h2>Acceptance criteria</h2><LabelList items={ticket.acceptance_criteria} empty="No acceptance criteria yet." /></section>
              <section className="detail-section"><h2>Definition of done</h2><LabelList items={ticket.definition_of_done} empty="No definition of done yet." /></section>
              <section className="detail-section"><h2>Constraints</h2><LabelList items={ticket.constraints} empty="No constraints." /></section>
              <section className="detail-section"><h2>Context</h2><LabelList items={ticket.context} empty="No additional context." /></section>
            </main>
            <aside className="ticket-detail-aside">
              <section className="detail-panel"><span>Priority</span><strong>{ticket.priority}</strong></section>
              <section className="detail-panel"><span>Complexity</span><strong>{ticket.estimated_complexity || "—"}</strong></section>
              <section className="detail-panel"><span>Parent</span><strong>{ticket.parent_id || "—"}</strong></section>
              <section className="detail-panel"><span>Dependencies</span><strong>{ticket.dependency_ids.length || "None"}</strong>{ticket.dependency_ids.map((id) => <code key={id}>{id}</code>)}</section>
              <section className="detail-panel"><span>Blocked by</span><strong>{ticket.blocked_by_ids.length || "None"}</strong></section>
              <section className="detail-panel"><span>Human required</span><strong>{ticket.requires_human ? "Yes" : "No"}</strong></section>
              <section className="detail-panel"><span>Relevant files</span>{ticket.relevant_files.length === 0 && <strong>None</strong>}{ticket.relevant_files.map((file) => <code key={file}>{file}</code>)}</section>
            </aside>
          </div>
        </>
      )}

      <section className="detail-section detail-activity">
        <h2>Activity</h2>
        {events.length === 0 && <p className="detail-empty">No recorded activity yet.</p>}
        <div className="activity-timeline">{[...events].reverse().map((event) => <article className="activity-event" key={event.id}><span className="activity-dot" /><div><strong>{eventSummary(event)}</strong><p>{event.actor} · {new Date(event.created_at).toLocaleString()}</p></div></article>)}</div>
      </section>
    </section>
  );
}
