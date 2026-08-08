import { FormEvent, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useParams, useSearchParams } from "react-router-dom";

import RepositoryPage from "./RepositoryPage";
import TicketDetail from "./TicketDetail";
import { getProject, listProjects, type Project } from "./api/projects";
import {
  createTicket,
  listTickets,
  updateTicket,
  type Ticket,
  type TicketPriority,
  type TicketStatus,
  type TicketType,
} from "./api/tickets";

const FLOW_COLUMNS: Array<{ status: TicketStatus; label: string }> = [
  { status: "backlog", label: "Backlog" },
  { status: "ready", label: "Ready" },
  { status: "in_progress", label: "In Progress" },
  { status: "review", label: "Review" },
  { status: "done", label: "Done" },
];

const ATTENTION_STATUSES: Array<{ status: TicketStatus; label: string }> = [
  { status: "blocked", label: "Blocked" },
  { status: "needs_human", label: "Needs Human" },
  { status: "agent_failed", label: "Agent Failed" },
];

const ACTIVE_CHILD_STATUSES: TicketStatus[] = ["ready", "in_progress", "review"];
const ATTENTION_CHILD_STATUSES: TicketStatus[] = ["needs_human", "agent_failed"];
type ProjectView = "board" | "epics";

type ProjectFilters = {
  type: string;
  priority: string;
  status: string;
  parent: string;
};

function displayTitle(ticket: Ticket): string {
  const prefix = `${ticket.ticket_key} `;
  return ticket.title.startsWith(prefix) ? ticket.title.slice(prefix.length) : ticket.title;
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load projects"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">AD</div><div><strong>AgentDesk</strong><span>Engineering cockpit</span></div></div>
        <div className="sidebar-section">
          <div className="sidebar-heading">Projects</div>
          {loading && <div className="sidebar-muted">Loading…</div>}
          {error && <div className="sidebar-error">API unavailable</div>}
          {!loading && !error && projects.length === 0 && <div className="sidebar-muted">No projects yet</div>}
          <nav className="project-nav">
            {projects.map((project) => (
              <div className="project-nav-group" key={project.id}>
                <NavLink to={`/projects/${project.id}`} end className={({ isActive }) => `project-link${isActive ? " active" : ""}`}><span className="project-dot" />{project.name}</NavLink>
                <NavLink to={`/projects/${project.id}/repositories`} className={({ isActive }) => `project-sub-link${isActive ? " active" : ""}`}>Repositories</NavLink>
              </div>
            ))}
          </nav>
        </div>
      </aside>
      <main className="main-panel">
        <Routes>
          <Route path="/" element={<Home projects={projects} loading={loading} error={error} />} />
          <Route path="/projects/:projectId" element={<ProjectBoard />} />
          <Route path="/projects/:projectId/repositories" element={<RepositoryPage />} />
          <Route path="/tickets/:ticketId" element={<TicketDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function Home({ projects, loading, error }: { projects: Project[]; loading: boolean; error: string | null }) {
  return <section className="page"><header className="page-header"><div><div className="eyebrow">Workspace</div><h1>Projects</h1><p>Select a project to inspect its current workspace.</p></div></header>{error && <div className="notice error-notice"><strong>Could not reach AgentDesk API.</strong><span>{error}</span></div>}{!error && !loading && <div className="project-grid">{projects.map((project) => <NavLink className="project-card" key={project.id} to={`/projects/${project.id}`}><div className="project-card-topline"><span className="project-badge">Project</span>{project.archived && <span className="archived-badge">Archived</span>}</div><h2>{project.name}</h2><p>{project.description || "No description yet."}</p><span className="card-action">Open project →</span></NavLink>)}</div>}</section>;
}

function ProjectBoard() {
  const { projectId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [project, setProject] = useState<Project | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const view: ProjectView = searchParams.get("view") === "epics" ? "epics" : "board";
  const showCompleted = searchParams.get("completed") === "1";
  const filters: ProjectFilters = {
    type: searchParams.get("type") ?? "",
    priority: searchParams.get("priority") ?? "",
    status: searchParams.get("status") ?? "",
    parent: searchParams.get("parent") ?? "",
  };

  function setParam(name: string, value: string) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(name, value); else next.delete(name);
      return next;
    });
  }

  function clearFilters() {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      ["type", "priority", "status", "parent"].forEach((name) => next.delete(name));
      return next;
    });
  }

  useEffect(() => {
    if (!projectId) return;
    setLoading(true); setError(null);
    Promise.all([getProject(projectId), listTickets(projectId)])
      .then(([nextProject, nextTickets]) => { setProject(nextProject); setTickets(nextTickets); })
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load project"))
      .finally(() => setLoading(false));
  }, [projectId]);

  const epicOptions = useMemo(() => tickets.filter((ticket) => ticket.type === "epic"), [tickets]);
  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  function matchesFilters(ticket: Ticket): boolean {
    if (filters.type && ticket.type !== filters.type) return false;
    if (filters.priority && ticket.priority !== filters.priority) return false;
    if (filters.status && ticket.status !== filters.status) return false;
    if (filters.parent && ticket.parent_id !== filters.parent) return false;
    return true;
  }

  const attentionTickets = useMemo(
    () => tickets.filter((ticket) => ATTENTION_STATUSES.some(({ status }) => status === ticket.status)).filter(matchesFilters),
    [tickets, filters.type, filters.priority, filters.status, filters.parent],
  );
  const boardTickets = useMemo(
    () => tickets.filter((ticket) => ticket.type !== "epic" && (showCompleted || ticket.status !== "done")).filter(matchesFilters),
    [tickets, showCompleted, filters.type, filters.priority, filters.status, filters.parent],
  );
  const epicTickets = useMemo(
    () => tickets.filter((ticket) => ticket.type === "epic" && (showCompleted || ticket.status !== "done")).filter(matchesFilters),
    [tickets, showCompleted, filters.type, filters.priority, filters.status, filters.parent],
  );
  const visibleColumns = (showCompleted ? FLOW_COLUMNS : FLOW_COLUMNS.filter(({ status }) => status !== "done"))
    .filter(({ status }) => !filters.status || status === filters.status);

  async function moveTicket(ticketId: string, status: TicketStatus) {
    const current = tickets.find((ticket) => ticket.id === ticketId);
    if (!current || current.status === status) return;
    const snapshot = tickets;
    setTickets((items) => items.map((ticket) => ticket.id === ticketId ? { ...ticket, status } : ticket));
    try { const updated = await updateTicket(ticketId, { status }); setTickets((items) => items.map((ticket) => ticket.id === ticketId ? updated : ticket)); setError(null); }
    catch (cause) { setTickets(snapshot); setError(cause instanceof Error ? cause.message : "Unable to move ticket"); }
  }

  async function addTicket(payload: { title: string; type: TicketType; priority: TicketPriority }) {
    if (!projectId) return;
    setCreating(true);
    try { const ticket = await createTicket(projectId, payload); setTickets((items) => [...items, ticket]); setError(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to create ticket"); }
    finally { setCreating(false); }
  }

  if (loading) return <section className="page loading-page">Loading project…</section>;
  if (!project) return <section className="page loading-page">Project unavailable.</section>;

  return (
    <section className="page board-page">
      <header className="page-header project-header"><div><div className="eyebrow">Project</div><h1>{project.name}</h1><p>{project.description || "No description yet."}</p></div><div className="status-chip">{project.archived ? "Archived" : "Active"}</div></header>
      <TicketComposer onCreate={addTicket} busy={creating} />
      <div className="project-view-toolbar">
        <div className="project-view-tabs" role="tablist" aria-label="Project view">
          <button type="button" className={view === "board" ? "active" : ""} onClick={() => setParam("view", "")}>Board</button>
          <button type="button" className={view === "epics" ? "active" : ""} onClick={() => setParam("view", "epics")}>Epics</button>
        </div>
        <label className="show-completed-toggle"><input type="checkbox" checked={showCompleted} onChange={(event) => setParam("completed", event.target.checked ? "1" : "")} /> Show completed</label>
      </div>
      <div className="project-filter-bar">
        <select aria-label="Filter by type" value={filters.type} onChange={(event) => setParam("type", event.target.value)}>
          <option value="">All types</option><option value="story">Story</option><option value="task">Task</option><option value="bug">Bug</option><option value="spike">Spike</option><option value="epic">Epic</option>
        </select>
        <select aria-label="Filter by priority" value={filters.priority} onChange={(event) => setParam("priority", event.target.value)}>
          <option value="">All priorities</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
        </select>
        <select aria-label="Filter by status" value={filters.status} onChange={(event) => setParam("status", event.target.value)}>
          <option value="">All statuses</option>{[...FLOW_COLUMNS, ...ATTENTION_STATUSES].map(({ status, label }) => <option key={status} value={status}>{label}</option>)}
        </select>
        <select aria-label="Filter by epic" value={filters.parent} onChange={(event) => setParam("parent", event.target.value)}>
          <option value="">All epics</option>{epicOptions.map((epic) => <option key={epic.id} value={epic.id}>{epic.ticket_key} — {displayTitle(epic)}</option>)}
        </select>
        {activeFilterCount > 0 && <button className="clear-project-filters" type="button" onClick={clearFilters}>Clear {activeFilterCount}</button>}
      </div>
      {error && <div className="notice error-notice board-error"><strong>Board action failed.</strong><span>{error}</span></div>}
      {attentionTickets.length > 0 && <div className="attention-strip">{ATTENTION_STATUSES.map(({ status, label }) => { const items = attentionTickets.filter((ticket) => ticket.status === status); if (!items.length) return null; return <div key={status} className={`attention-group ${status}`}><span>{label}</span><strong>{items.length}</strong><div className="attention-items">{items.map((ticket) => <NavLink key={ticket.id} to={`/tickets/${ticket.id}`}>{ticket.ticket_key}</NavLink>)}</div></div>; })}</div>}
      {view === "board" ? (
        visibleColumns.length > 0 ? <div className={`kanban-board${showCompleted ? " with-done" : ""}`} style={{ gridTemplateColumns: `repeat(${visibleColumns.length}, minmax(230px, 1fr))` }}>
          {visibleColumns.map(({ status, label }) => { const columnTickets = boardTickets.filter((ticket) => ticket.status === status); return <section className="kanban-column" key={status} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); const ticketId = event.dataTransfer.getData("text/plain"); if (ticketId) void moveTicket(ticketId, status); }}><header className="kanban-column-header"><span>{label}</span><span className="column-count">{columnTickets.length}</span></header><div className="kanban-stack">{columnTickets.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} />)}{columnTickets.length === 0 && <div className="column-empty">No matching tickets</div>}</div></section>; })}
        </div> : <div className="epic-grid-empty">This status is shown in the attention strip rather than a board column.</div>
      ) : <EpicGrid epics={epicTickets} tickets={tickets} />}
    </section>
  );
}

function EpicGrid({ epics, tickets }: { epics: Ticket[]; tickets: Ticket[] }) {
  if (epics.length === 0) return <div className="epic-grid-empty">No epics match the current view and filters.</div>;
  return <div className="epic-grid">{epics.map((epic) => <EpicCard key={epic.id} epic={epic} children={tickets.filter((ticket) => ticket.parent_id === epic.id)} />)}</div>;
}

function EpicCard({ epic, children }: { epic: Ticket; children: Ticket[] }) {
  const counted = children.filter((ticket) => ticket.status !== "cancelled");
  const done = counted.filter((ticket) => ticket.status === "done").length;
  const active = counted.filter((ticket) => ACTIVE_CHILD_STATUSES.includes(ticket.status)).length;
  const blocked = counted.filter((ticket) => ticket.status === "blocked").length;
  const attention = counted.filter((ticket) => ATTENTION_CHILD_STATUSES.includes(ticket.status)).length;
  const percent = counted.length ? Math.round((done / counted.length) * 100) : 0;
  return <NavLink className="epic-card" to={`/tickets/${epic.id}`}><div className="epic-card-topline"><span className="ticket-key">{epic.ticket_key}</span><span className={`detail-status status-${epic.status}`}>{epic.status.replaceAll("_", " ")}</span></div><h2>{displayTitle(epic)}</h2><div className="epic-card-progress"><div><span>Progress</span><strong>{percent}%</strong></div><div className="epic-card-progress-track"><span style={{ width: `${percent}%` }} /></div></div><div className="epic-card-counts"><span><b>{done}</b> done</span><span><b>{active}</b> active</span><span><b>{blocked}</b> blocked</span><span><b>{attention}</b> attention</span></div><div className="epic-card-footer"><span>{counted.length} child ticket{counted.length === 1 ? "" : "s"}</span><span>Open roadmap →</span></div></NavLink>;
}

function TicketComposer({ onCreate, busy }: { onCreate: (payload: { title: string; type: TicketType; priority: TicketPriority }) => Promise<void>; busy: boolean }) {
  const [title, setTitle] = useState(""); const [type, setType] = useState<TicketType>("story"); const [priority, setPriority] = useState<TicketPriority>("medium");
  async function submit(event: FormEvent) { event.preventDefault(); const cleanTitle = title.trim(); if (!cleanTitle) return; await onCreate({ title: cleanTitle, type, priority }); setTitle(""); }
  return <form className="ticket-composer" onSubmit={submit}><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Create a ticket…" aria-label="Ticket title" /><select value={type} onChange={(event) => setType(event.target.value as TicketType)} aria-label="Ticket type"><option value="story">Story</option><option value="task">Task</option><option value="bug">Bug</option><option value="spike">Spike</option><option value="epic">Epic</option></select><select value={priority} onChange={(event) => setPriority(event.target.value as TicketPriority)} aria-label="Ticket priority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select><button type="submit" disabled={busy || !title.trim()}>{busy ? "Creating…" : "Create"}</button></form>;
}

function TicketCard({ ticket }: { ticket: Ticket }) {
  return <article className={`ticket-card priority-${ticket.priority}`} draggable onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", ticket.id); }}><NavLink className="ticket-card-link" to={`/tickets/${ticket.id}`}><div className="ticket-card-meta"><span className="ticket-key">{ticket.ticket_key}</span><span className={`ticket-type type-${ticket.type}`}>{ticket.type}</span></div><h3>{displayTitle(ticket)}</h3><div className="ticket-card-footer"><span className={`priority-pill ${ticket.priority}`}>{ticket.priority}</span>{ticket.assignee && <span className="assignee">{ticket.assignee}</span>}</div></NavLink></article>;
}

export default App;
