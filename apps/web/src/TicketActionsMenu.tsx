import { useEffect, useRef, useState } from "react";

import type { Ticket } from "./api/tickets";
import TicketLifecycleActions from "./TicketLifecycleActions";
import TicketRelationships from "./TicketRelationships";

type ModalKind = "relationships" | "lifecycle" | null;

export default function TicketActionsMenu({
  ticket,
  onEdit,
  onChanged,
}: {
  ticket: Ticket;
  onEdit: () => void;
  onChanged: () => Promise<void>;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [modal, setModal] = useState<ModalKind>(null);
  const menuRef = useRef<HTMLDivElement>(null);

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

  function openModal(kind: Exclude<ModalKind, null>) {
    setMenuOpen(false);
    setModal(kind);
  }

  return (
    <>
      <div className="ticket-actions-menu" ref={menuRef}>
        <button className="ticket-actions-trigger" type="button" onClick={() => setMenuOpen((value) => !value)}>
          Actions <span>▾</span>
        </button>
        {menuOpen && (
          <div className="ticket-actions-popover">
            <button type="button" onClick={() => { setMenuOpen(false); onEdit(); }}>
              <strong>Edit ticket</strong><span>Change story fields and status</span>
            </button>
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
              <div>
                <span>{ticket.ticket_key}</span>
                <h2>{modal === "relationships" ? "Relationships" : "Lifecycle"}</h2>
              </div>
              <button type="button" aria-label="Close" onClick={() => setModal(null)}>×</button>
            </header>
            <div className="ticket-modal-body">
              {modal === "relationships" && <TicketRelationships ticket={ticket} onChanged={onChanged} />}
              {modal === "lifecycle" && <TicketLifecycleActions ticket={ticket} onChanged={onChanged} />}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
