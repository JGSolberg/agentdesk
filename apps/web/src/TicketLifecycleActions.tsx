import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteTicket, updateTicket, type Ticket } from "./api/tickets";
import TicketRelationships from "./TicketRelationships";

type ModalKind = "relationships" | "lifecycle" | null;

export default function TicketLifecycleActions({ ticket, onChanged }: { ticket: Ticket; onChanged: () => Promise<void> }) {
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [modal, setModal] = useState<ModalKind>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        setModal(null);
      }
    }
    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

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

  function openModal(kind: Exclude<ModalKind, null>) {
    setMenuOpen(false);
    setError(null);
    setModal(kind);
  }

  return (
    <div className="ticket-lifecycle-wrap">
      <div className="ticket-actions-menu" ref={menuRef}>
        <button className="ticket-actions-trigger" type="button" onClick={() => setMenuOpen((value) => !value)}>
          Actions <span>▾</span>
        </button>
        {menuOpen && (
          <div className="ticket-actions-popover">
            <button type="button" onClick={() => openModal("relationships")}>
              <strong>Relationships</strong><span>Parent, dependencies, blockers</span>
            </button>
            <button type="button" onClick={() => openModal("lifecycle")}>
              <strong>Lifecycle</strong><span>Cancel, archive, or delete</span>
            </button>
          </div>
        )}
      </div>

      {modal && (
        <div className="ticket-modal-backdrop" role="presentation" onMouseDown={() => setModal(null)}>
          <section className="ticket-modal" role="dialog" aria-modal="true" aria-label={modal === "relationships" ? "Ticket relationships" : "Ticket lifecycle"} onMouseDown={(event) => event.stopPropagation()}>
            <header className="ticket-modal-header">
              <div><span>{ticket.ticket_key}</span><h2>{modal === "relationships" ? "Relationships" : "Lifecycle"}</h2></div>
              <button type="button" aria-label="Close" onClick={() => setModal(null)}>×</button>
            </header>
            <div className="ticket-modal-body">
              {modal === "relationships" ? (
                <TicketRelationships ticket={ticket} onChanged={onChanged} />
              ) : (
                <div className="lifecycle-modal-content">
                  <p>Cancel keeps the ticket visible, archive removes it from the normal board, and delete permanently removes disposable tickets.</p>
                  <div className="ticket-lifecycle-actions">
                    <button type="button" disabled={busy || ticket.archived} onClick={() => void mutate(() => updateTicket(ticket.id, { status: ticket.status === "cancelled" ? "backlog" : "cancelled" }))}>
                      {ticket.status === "cancelled" ? "Reopen" : "Cancel ticket"}
                    </button>
                    <button type="button" disabled={busy} onClick={() => void mutate(() => updateTicket(ticket.id, { archived: !ticket.archived }))}>
                      {ticket.archived ? "Unarchive" : "Archive"}
                    </button>
                    <button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>Delete permanently</button>
                  </div>
                  {ticket.archived && <span className="ticket-lifecycle-note">Archived tickets are hidden from the project board but remain searchable.</span>}
                  {error && <span className="ticket-lifecycle-error">{error}</span>}
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
