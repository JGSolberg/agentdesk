import { FormEvent, useEffect, useRef, useState } from "react";

import type { Ticket, TicketCreate, TicketPriority, TicketStatus, TicketType } from "./api/tickets";

function lines(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

export default function TicketCreatePanel({ epics, busy, onCreate }: { epics: Ticket[]; busy: boolean; onCreate: (payload: TicketCreate) => Promise<void> }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<TicketType>("story");
  const [status, setStatus] = useState<TicketStatus>("backlog");
  const [priority, setPriority] = useState<TicketPriority>("medium");

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const title = String(data.get("title") ?? "").trim();
    if (!title) return;
    await onCreate({
      title,
      type,
      status,
      priority,
      parent_id: String(data.get("parent_id") ?? "") || null,
      goal: String(data.get("goal") ?? "").trim() || null,
      description: String(data.get("description") ?? "").trim() || null,
      acceptance_criteria: lines(String(data.get("acceptance_criteria") ?? "")),
      estimated_complexity: String(data.get("estimated_complexity") ?? "").trim() || null,
      requires_human: data.get("requires_human") === "on",
    });
    form.reset();
    setType("story");
    setStatus("backlog");
    setPriority("medium");
    setOpen(false);
  }

  return (
    <div className="ticket-create-wrap" ref={rootRef}>
      <button className="ticket-create-trigger" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>+ Create ticket</button>
      {open && (
        <form className="ticket-create-panel" onSubmit={submit}>
          <header><div><span>New ticket</span><strong>Create useful work, not an empty shell</strong></div><button type="button" onClick={() => setOpen(false)}>×</button></header>
          <label className="ticket-create-title">Title<input name="title" autoFocus required placeholder="What needs to be done?" /></label>
          <div className="ticket-create-grid four-up">
            <label>Type<select value={type} onChange={(event) => setType(event.target.value as TicketType)}><option value="story">Story</option><option value="task">Task</option><option value="bug">Bug</option><option value="spike">Spike</option><option value="epic">Epic</option></select></label>
            <label>Status<select value={status} onChange={(event) => setStatus(event.target.value as TicketStatus)}><option value="backlog">Backlog</option><option value="ready">Ready</option><option value="in_progress">In Progress</option><option value="blocked">Blocked</option><option value="needs_human">Needs Human</option></select></label>
            <label>Priority<select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label>
            <label>Complexity<input name="estimated_complexity" placeholder="small / medium / large" /></label>
          </div>
          {type !== "epic" && <label>Parent epic<select name="parent_id" defaultValue=""><option value="">None</option>{epics.map((epic) => <option key={epic.id} value={epic.id}>{epic.ticket_key} — {epic.title}</option>)}</select></label>}
          <label>Goal<textarea name="goal" rows={2} placeholder="What outcome should this produce?" /></label>
          <label>Description<textarea name="description" rows={4} placeholder="Enough context for someone else to pick this up." /></label>
          <label>Acceptance criteria <span>one per line</span><textarea name="acceptance_criteria" rows={5} placeholder={"User can...\nSystem prevents...\nTests cover..."} /></label>
          <label className="ticket-create-checkbox"><input name="requires_human" type="checkbox" /> Requires human attention</label>
          <footer><button type="button" onClick={() => setOpen(false)}>Cancel</button><button type="submit" disabled={busy}>{busy ? "Creating…" : "Create ticket"}</button></footer>
        </form>
      )}
    </div>
  );
}
