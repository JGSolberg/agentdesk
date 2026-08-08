import { useEffect, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";

import {
  addTicketDependency,
  listTickets,
  removeTicketDependency,
  updateTicket,
  type Ticket,
} from "./api/tickets";

export default function TicketRelationships({ ticket, onChanged }: { ticket: Ticket; onChanged: () => Promise<void> | void }) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [dependencyId, setDependencyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTickets(ticket.project_id, true)
      .then(setTickets)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load relationships"));
  }, [ticket.project_id, ticket.id]);

  const byId = useMemo(() => new Map(tickets.map((item) => [item.id, item])), [tickets]);
  const parent = ticket.parent_id ? byId.get(ticket.parent_id) : undefined;
  const dependencies = ticket.dependency_ids.map((id) => byId.get(id)).filter((item): item is Ticket => Boolean(item));
  const dependencyOptions = tickets.filter(
    (item) => item.id !== ticket.id && !ticket.dependency_ids.includes(item.id),
  );
  const parentOptions = tickets.filter((item) => item.id !== ticket.id);

  async function changeParent(parentId: string) {
    setBusy(true);
    setError(null);
    try {
      await updateTicket(ticket.id, { parent_id: parentId || null });
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to change parent");
    } finally {
      setBusy(false);
    }
  }

  async function addDependency() {
    if (!dependencyId) return;
    setBusy(true);
    setError(null);
    try {
      await addTicketDependency(ticket.id, dependencyId);
      setDependencyId("");
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to add dependency");
    } finally {
      setBusy(false);
    }
  }

  async function removeDependency(id: string) {
    setBusy(true);
    setError(null);
    try {
      await removeTicketDependency(ticket.id, id);
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to remove dependency");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="detail-panel relationship-panel">
      <span>Relationships</span>

      <div className="relationship-group">
        <label htmlFor="ticket-parent">Parent</label>
        {parent && (
          <NavLink className="relationship-link" to={`/tickets/${parent.id}`}>
            <strong>{parent.ticket_key}</strong>
            <small>{parent.title}{parent.archived ? " · archived" : ""}</small>
          </NavLink>
        )}
        {!parent && ticket.parent_id && <code>{ticket.parent_id}</code>}
        <select id="ticket-parent" value={ticket.parent_id ?? ""} disabled={busy} onChange={(event) => void changeParent(event.target.value)}>
          <option value="">No parent</option>
          {parentOptions.map((item) => (
            <option key={item.id} value={item.id}>{item.ticket_key} — {item.title}{item.archived ? " (archived)" : ""}</option>
          ))}
        </select>
      </div>

      <div className="relationship-group">
        <label>Dependencies</label>
        {dependencies.length === 0 && <strong className="relationship-empty">None</strong>}
        <div className="relationship-list">
          {dependencies.map((dependency) => (
            <div className="relationship-item" key={dependency.id}>
              <NavLink className="relationship-link" to={`/tickets/${dependency.id}`}>
                <strong>{dependency.ticket_key}</strong>
                <small>{dependency.title}{dependency.archived ? " · archived" : ""}</small>
              </NavLink>
              <button type="button" disabled={busy} onClick={() => void removeDependency(dependency.id)}>×</button>
            </div>
          ))}
          {ticket.dependency_ids.filter((id) => !byId.has(id)).map((id) => <code key={id}>{id}</code>)}
        </div>
        <div className="relationship-add">
          <select value={dependencyId} disabled={busy} onChange={(event) => setDependencyId(event.target.value)}>
            <option value="">Add dependency…</option>
            {dependencyOptions.map((item) => (
              <option key={item.id} value={item.id}>{item.ticket_key} — {item.title}{item.archived ? " (archived)" : ""}</option>
            ))}
          </select>
          <button type="button" disabled={busy || !dependencyId} onClick={() => void addDependency()}>Add</button>
        </div>
      </div>

      <div className="relationship-group">
        <label>Blocked by</label>
        {ticket.blocked_by_ids.length === 0 && <strong className="relationship-empty">None</strong>}
        {ticket.blocked_by_ids.map((id) => {
          const blocker = byId.get(id);
          return blocker ? (
            <NavLink className="relationship-link compact" key={id} to={`/tickets/${id}`}>
              <strong>{blocker.ticket_key}</strong><small>{blocker.title}</small>
            </NavLink>
          ) : <code key={id}>{id}</code>;
        })}
      </div>

      {error && <div className="relationship-error">{error}</div>}
    </section>
  );
}
