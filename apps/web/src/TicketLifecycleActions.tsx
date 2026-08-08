import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteTicket, updateTicket, type Ticket } from "./api/tickets";

export default function TicketLifecycleActions({ ticket, onChanged }: { ticket: Ticket; onChanged: () => Promise<void> }) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function mutate(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ticket lifecycle action failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Permanently delete ${ticket.ticket_key}? This cannot be undone.`)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteTicket(ticket.id);
      navigate(`/projects/${ticket.project_id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete ticket");
      setBusy(false);
    }
  }

  return (
    <div className="ticket-lifecycle-wrap">
      <div className="ticket-lifecycle-actions">
        <button
          type="button"
          disabled={busy || ticket.archived}
          onClick={() => void mutate(() => updateTicket(ticket.id, { status: ticket.status === "cancelled" ? "backlog" : "cancelled" }))}
        >
          {ticket.status === "cancelled" ? "Reopen" : "Cancel ticket"}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void mutate(() => updateTicket(ticket.id, { archived: !ticket.archived }))}
        >
          {ticket.archived ? "Unarchive" : "Archive"}
        </button>
        <button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>
          Delete
        </button>
      </div>
      {ticket.archived && <span className="ticket-lifecycle-note">Archived tickets are hidden from the project board.</span>}
      {error && <span className="ticket-lifecycle-error">{error}</span>}
    </div>
  );
}
