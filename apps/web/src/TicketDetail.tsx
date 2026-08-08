import { useEffect, useState } from "react";
import { NavLink, useParams } from "react-router-dom";

import { getTicket, type Ticket } from "./api/tickets";

function LabelList({ items, empty }: { items: string[]; empty: string }) {
  if (items.length === 0) return <p className="detail-empty">{empty}</p>;
  return (
    <ul className="detail-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

export default function TicketDetail() {
  const { ticketId } = useParams();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticketId) return;
    setTicket(null);
    setError(null);
    getTicket(ticketId)
      .then(setTicket)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load ticket"));
  }, [ticketId]);

  if (error) {
    return (
      <section className="page">
        <div className="notice error-notice">
          <strong>Unable to load ticket.</strong>
          <span>{error}</span>
        </div>
      </section>
    );
  }

  if (!ticket) return <section className="page loading-page">Loading ticket…</section>;

  return (
    <section className="page ticket-detail-page">
      <NavLink className="detail-back" to={`/projects/${ticket.project_id}`}>
        ← Back to board
      </NavLink>

      <header className="ticket-detail-header">
        <div>
          <div className="ticket-detail-kicker">
            <span>{ticket.ticket_key}</span>
            <span>{ticket.type}</span>
          </div>
          <h1>{ticket.title}</h1>
        </div>
        <div className="ticket-detail-badges">
          <span className={`priority-pill ${ticket.priority}`}>{ticket.priority}</span>
          <span className={`detail-status status-${ticket.status}`}>{ticket.status.replaceAll("_", " ")}</span>
        </div>
      </header>

      <div className="ticket-detail-grid">
        <main className="ticket-detail-main">
          <section className="detail-section">
            <h2>Goal</h2>
            <p>{ticket.goal || "No goal provided."}</p>
          </section>

          <section className="detail-section">
            <h2>Description</h2>
            <p className="detail-description">{ticket.description || "No description provided."}</p>
          </section>

          <section className="detail-section">
            <h2>Acceptance criteria</h2>
            <LabelList items={ticket.acceptance_criteria} empty="No acceptance criteria yet." />
          </section>

          <section className="detail-section">
            <h2>Definition of done</h2>
            <LabelList items={ticket.definition_of_done} empty="No definition of done yet." />
          </section>

          <section className="detail-section">
            <h2>Constraints</h2>
            <LabelList items={ticket.constraints} empty="No constraints." />
          </section>

          <section className="detail-section">
            <h2>Context</h2>
            <LabelList items={ticket.context} empty="No additional context." />
          </section>
        </main>

        <aside className="ticket-detail-aside">
          <section className="detail-panel">
            <span>Priority</span>
            <strong>{ticket.priority}</strong>
          </section>
          <section className="detail-panel">
            <span>Complexity</span>
            <strong>{ticket.estimated_complexity || "—"}</strong>
          </section>
          <section className="detail-panel">
            <span>Parent</span>
            <strong>{ticket.parent_id || "—"}</strong>
          </section>
          <section className="detail-panel">
            <span>Dependencies</span>
            <strong>{ticket.dependency_ids.length ? ticket.dependency_ids.length : "None"}</strong>
            {ticket.dependency_ids.map((id) => <code key={id}>{id}</code>)}
          </section>
          <section className="detail-panel">
            <span>Blocked by</span>
            <strong>{ticket.blocked_by_ids.length ? ticket.blocked_by_ids.length : "None"}</strong>
          </section>
          <section className="detail-panel">
            <span>Human required</span>
            <strong>{ticket.requires_human ? "Yes" : "No"}</strong>
          </section>
          <section className="detail-panel">
            <span>Relevant files</span>
            {ticket.relevant_files.length === 0 && <strong>None</strong>}
            {ticket.relevant_files.map((file) => <code key={file}>{file}</code>)}
          </section>
        </aside>
      </div>

      <section className="detail-section detail-activity-placeholder">
        <h2>Activity</h2>
        <p>Ticket activity will appear here once the event ledger is implemented.</p>
      </section>
    </section>
  );
}
