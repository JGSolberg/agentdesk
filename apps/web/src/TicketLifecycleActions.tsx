import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteTicket, updateTicket, type Ticket } from "./api/tickets";
import TicketRelationships from "./TicketRelationships";

type Pane = "menu" | "relationships" | "lifecycle";

export default function TicketLifecycleActions({ ticket, onChanged, onEdit }: { ticket: Ticket; onChanged: () => Promise<void>; onEdit: () => void }) {
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [pane, setPane] = useState<Pane>("menu");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function close() {
      setOpen(false);
      setPane("menu");
    }
    function onPointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) close();
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") close();
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

  function toggle() {
    setOpen((value) => {
      if (value) setPane("menu");
      return !value;
    });
    setError(null);
  }

  function edit() {
    setOpen(false);
    setPane("menu");
    onEdit();
  }

  return (
    <div className="ticket-lifecycle-wrap">
      <div className="ticket-actions-menu" ref={menuRef}>
        <button className="ticket-actions-trigger" type="button" onClick={toggle} aria-expanded={open}>
          Actions <span>▾</span>
        </button>

        {open && (
          <div className={`ticket-actions-popover${pane === "menu" ? "" : " expanded"}`}>
            {pane === "menu" ? (
              <>
                <button type="button" onClick={edit}>
                  <strong>Edit ticket</strong><span>Title, status, criteria, and details</span>
                </button>
                <button type="button" onClick={() => setPane("relationships")}>
                  <strong>Relationships</strong><span>Parent, dependencies, blockers</span><b>›</b>
                </button>
                <button type="button" onClick={() => setPane("lifecycle")}>
                  <strong>Lifecycle</strong><span>Cancel, archive, or delete</span><b>›</b>
                </button>
              </>
            ) : (
              <>
                <header className="ticket-actions-panel-header">
                  <button type="button" className="ticket-actions-back" onClick={() => setPane("menu")}>← Back</button>
                  <div><span>{ticket.ticket_key}</span><strong>{pane === "relationships" ? "Relationships" : "Lifecycle"}</strong></div>
                </header>
                <div className="ticket-actions-panel-body">
                  {pane === "relationships" ? (
                    <TicketRelationships ticket={ticket} onChanged={onChanged} />
                  ) : (
                    <div className="lifecycle-menu-content">
                      <p>Cancel keeps the ticket visible. Archive hides it from the board. Delete permanently removes disposable tickets.</p>
                      <div className="ticket-lifecycle-actions">
                        <button type="button" disabled={busy || ticket.archived} onClick={() => void mutate(() => updateTicket(ticket.id, { status: ticket.status === "cancelled" ? "backlog" : "cancelled" }))}>
                          {ticket.status === "cancelled" ? "Reopen" : "Cancel ticket"}
                        </button>
                        <button type="button" disabled={busy} onClick={() => void mutate(() => updateTicket(ticket.id, { archived: !ticket.archived }))}>
                          {ticket.archived ? "Unarchive" : "Archive"}
                        </button>
                        <button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>Delete permanently</button>
                      </div>
                      {ticket.archived && <span className="ticket-lifecycle-note">Archived tickets remain searchable.</span>}
                      {error && <span className="ticket-lifecycle-error">{error}</span>}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
