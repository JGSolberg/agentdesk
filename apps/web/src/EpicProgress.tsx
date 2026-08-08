import { useEffect, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";

import { listTickets, type Ticket } from "./api/tickets";

function displayTitle(ticket: Ticket): string {
  const prefix = `${ticket.ticket_key} `;
  return ticket.title.startsWith(prefix) ? ticket.title.slice(prefix.length) : ticket.title;
}

export default function EpicProgress({ epic }: { epic: Ticket }) {
  const [children, setChildren] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    listTickets(epic.project_id, true)
      .then((tickets) => {
        if (!cancelled) setChildren(tickets.filter((ticket) => ticket.parent_id === epic.id));
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Unable to load epic progress");
      });
    return () => { cancelled = true; };
  }, [epic.id, epic.project_id]);

  const summary = useMemo(() => {
    const planned = children.filter((ticket) => ticket.status !== "cancelled");
    const done = planned.filter((ticket) => ticket.status === "done").length;
    const active = planned.filter((ticket) => ticket.status === "in_progress" || ticket.status === "review").length;
    const blocked = planned.filter((ticket) => ticket.is_blocked || ticket.status === "blocked").length;
    const attention = planned.filter((ticket) => ticket.status === "needs_human" || ticket.status === "agent_failed").length;
    const remaining = Math.max(0, planned.length - done);
    const percent = planned.length === 0 ? 0 : Math.round((done / planned.length) * 100);
    return { total: planned.length, done, active, blocked, attention, remaining, percent };
  }, [children]);

  return (
    <section className="detail-section epic-progress">
      <div className="epic-progress-heading">
        <div><h2>Epic progress</h2><p>Derived from direct child tickets.</p></div>
        <strong>{summary.percent}%</strong>
      </div>
      <div className="epic-progress-track" aria-label={`${summary.percent}% complete`}><span style={{ width: `${summary.percent}%` }} /></div>
      <div className="epic-progress-stats">
        <span><b>{summary.done}</b> done</span>
        <span><b>{summary.active}</b> active</span>
        <span><b>{summary.blocked}</b> blocked</span>
        <span><b>{summary.attention}</b> attention</span>
        <span><b>{summary.remaining}</b> remaining</span>
      </div>
      {error && <p className="workspace-status-error">{error}</p>}
      {!error && children.length === 0 && <p className="detail-empty">No child tickets yet.</p>}
      {children.length > 0 && (
        <div className="epic-child-list">
          {[...children].sort((a, b) => a.order - b.order || a.sequence - b.sequence).map((child) => (
            <NavLink className={`epic-child-row status-${child.status}`} to={`/tickets/${child.id}`} key={child.id}>
              <div className="epic-child-main">
                <span className="epic-child-key">{child.ticket_key}</span>
                <strong>{displayTitle(child)}</strong>
                {child.archived && <span className="epic-child-archived">archived</span>}
              </div>
              <div className="epic-child-meta">
                {child.is_blocked && <span>blocked</span>}
                <span>{child.status.replaceAll("_", " ")}</span>
                <span>{child.priority}</span>
              </div>
            </NavLink>
          ))}
        </div>
      )}
    </section>
  );
}
