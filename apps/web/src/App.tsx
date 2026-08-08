import { FormEvent, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useParams } from "react-router-dom";

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

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : "Unable to load projects");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AD</div>
          <div>
            <strong>AgentDesk</strong>
            <span>Engineering cockpit</span>
          </div>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-heading">Projects</div>
          {loading && <div className="sidebar-muted">Loading…</div>}
          {error && <div className="sidebar-error">API unavailable</div>}
          {!loading && !error && projects.length === 0 && (
            <div className="sidebar-muted">No projects yet</div>
          )}
          <nav className="project-nav">
            {projects.map((project) => (
              <NavLink
                key={project.id}
                to={`/projects/${project.id}`}
                className={({ isActive }) => `project-link${isActive ? " active" : ""}`}
              >
                <span className="project-dot" />
                {project.name}
              </NavLink>
            ))}
          </nav>
        </div>
      </aside>

      <main className="main-panel">
        <Routes>
          <Route path="/" element={<Home projects={projects} loading={loading} error={error} />} />
          <Route path="/projects/:projectId" element={<ProjectBoard />} />
          <Route path="/tickets/:ticketId" element={<TicketDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function Home({ projects, loading, error }: { projects: Project[]; loading: boolean; error: string | null }) {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Workspace</div>
          <h1>Projects</h1>
          <p>Select a project to inspect its current workspace.</p>
        </div>
      </header>

      {error && (
        <div className="notice error-notice">
          <strong>Could not reach AgentDesk API.</strong>
          <span>{error}</span>
        </div>
      )}

      {!error && !loading && (
        <div className="project-grid">
          {projects.map((project) => (
            <NavLink className="project-card" key={project.id} to={`/projects/${project.id}`}>
              <div className="project-card-topline">
                <span className="project-badge">Project</span>
                {project.archived && <span className="archived-badge">Archived</span>}
              </div>
              <h2>{project.name}</h2>
              <p>{project.description || "No description yet."}</p>
              <span className="card-action">Open project →</span>
            </NavLink>
          ))}
        </div>
      )}
    </section>
  );
}

function ProjectBoard() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    Promise.all([getProject(projectId), listTickets(projectId)])
      .then(([nextProject, nextTickets]) => {
        setProject(nextProject);
        setTickets(nextTickets);
      })
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load project"))
      .finally(() => setLoading(false));
  }, [projectId]);

  const attentionTickets = useMemo(
    () => tickets.filter((ticket) => ATTENTION_STATUSES.some(({ status }) => status === ticket.status)),
    [tickets],
  );

  async function moveTicket(ticketId: string, status: TicketStatus) {
    const current = tickets.find((ticket) => ticket.id === ticketId);
    if (!current || current.status === status) return;

    const snapshot = tickets;
    setTickets((items) => items.map((ticket) => (ticket.id === ticketId ? { ...ticket, status } : ticket)));
    try {
      const updated = await updateTicket(ticketId, { status });
      setTickets((items) => items.map((ticket) => (ticket.id === ticketId ? updated : ticket)));
      setError(null);
    } catch (cause) {
      setTickets(snapshot);
      setError(cause instanceof Error ? cause.message : "Unable to move ticket");
    }
  }

  async function addTicket(payload: { title: string; type: TicketType; priority: TicketPriority }) {
    if (!projectId) return;
    setCreating(true);
    try {
      const ticket = await createTicket(projectId, payload);
      setTickets((items) => [...items, ticket]);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create ticket");
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <section className="page loading-page">Loading project…</section>;
  if (!project) return <section className="page loading-page">Project unavailable.</section>;

  return (
    <section className="page board-page">
      <header className="page-header project-header">
        <div>
          <div className="eyebrow">Project</div>
          <h1>{project.name}</h1>
          <p>{project.description || "No description yet."}</p>
        </div>
        <div className="status-chip">{project.archived ? "Archived" : "Active"}</div>
      </header>

      <TicketComposer onCreate={addTicket} busy={creating} />

      {error && (
        <div className="notice error-notice board-error">
          <strong>Board action failed.</strong>
          <span>{error}</span>
        </div>
      )}

      {attentionTickets.length > 0 && (
        <div className="attention-strip">
          {ATTENTION_STATUSES.map(({ status, label }) => {
            const items = attentionTickets.filter((ticket) => ticket.status === status);
            if (!items.length) return null;
            return (
              <div key={status} className={`attention-group ${status}`}>
                <span>{label}</span>
                <strong>{items.length}</strong>
                <div className="attention-items">
                  {items.map((ticket) => (
                    <NavLink key={ticket.id} to={`/tickets/${ticket.id}`}>{ticket.ticket_key}</NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="kanban-board">
        {FLOW_COLUMNS.map(({ status, label }) => {
          const columnTickets = tickets.filter((ticket) => ticket.status === status);
          return (
            <section
              className="kanban-column"
              key={status}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                const ticketId = event.dataTransfer.getData("text/plain");
                if (ticketId) void moveTicket(ticketId, status);
              }}
            >
              <header className="kanban-column-header">
                <span>{label}</span>
                <span className="column-count">{columnTickets.length}</span>
              </header>
              <div className="kanban-stack">
                {columnTickets.map((ticket) => (
                  <TicketCard key={ticket.id} ticket={ticket} />
                ))}
                {columnTickets.length === 0 && <div className="column-empty">Drop tickets here</div>}
              </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}

function TicketComposer({
  onCreate,
  busy,
}: {
  onCreate: (payload: { title: string; type: TicketType; priority: TicketPriority }) => Promise<void>;
  busy: boolean;
}) {
  const [title, setTitle] = useState("");
  const [type, setType] = useState<TicketType>("story");
  const [priority, setPriority] = useState<TicketPriority>("medium");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const cleanTitle = title.trim();
    if (!cleanTitle) return;
    await onCreate({ title: cleanTitle, type, priority });
    setTitle("");
  }

  return (
    <form className="ticket-composer" onSubmit={submit}>
      <input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder="Create a ticket…"
        aria-label="Ticket title"
      />
      <select value={type} onChange={(event) => setType(event.target.value as TicketType)} aria-label="Ticket type">
        <option value="story">Story</option>
        <option value="task">Task</option>
        <option value="bug">Bug</option>
        <option value="spike">Spike</option>
        <option value="epic">Epic</option>
      </select>
      <select
        value={priority}
        onChange={(event) => setPriority(event.target.value as TicketPriority)}
        aria-label="Ticket priority"
      >
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
        <option value="critical">Critical</option>
      </select>
      <button type="submit" disabled={busy || !title.trim()}>
        {busy ? "Creating…" : "Create"}
      </button>
    </form>
  );
}

function TicketCard({ ticket }: { ticket: Ticket }) {
  return (
    <article
      className={`ticket-card priority-${ticket.priority}`}
      draggable
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", ticket.id);
      }}
    >
      <NavLink className="ticket-card-link" to={`/tickets/${ticket.id}`}>
        <div className="ticket-card-meta">
          <span className="ticket-key">{ticket.ticket_key}</span>
          <span className={`ticket-type type-${ticket.type}`}>{ticket.type}</span>
        </div>
        <h3>{ticket.title}</h3>
        <div className="ticket-card-footer">
          <span className={`priority-pill ${ticket.priority}`}>{ticket.priority}</span>
          {ticket.assignee && <span className="assignee">{ticket.assignee}</span>}
        </div>
      </NavLink>
    </article>
  );
}

export default App;
