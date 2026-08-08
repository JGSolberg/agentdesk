import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useParams } from "react-router-dom";

import { getProject, listProjects, type Project } from "./api/projects";

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
          <Route path="/projects/:projectId" element={<ProjectOverview />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function Home({
  projects,
  loading,
  error,
}: {
  projects: Project[];
  loading: boolean;
  error: string | null;
}) {
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
          {projects.length === 0 && (
            <div className="empty-state">
              <strong>No projects yet</strong>
              <span>Create one through the API for now; project creation UI comes with the board work.</span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ProjectOverview() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    setProject(null);
    setError(null);
    getProject(projectId)
      .then(setProject)
      .catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : "Unable to load project");
      });
  }, [projectId]);

  if (error) {
    return (
      <section className="page">
        <div className="notice error-notice">
          <strong>Unable to load project.</strong>
          <span>{error}</span>
        </div>
      </section>
    );
  }

  if (!project) {
    return <section className="page loading-page">Loading project…</section>;
  }

  return (
    <section className="page">
      <header className="page-header project-header">
        <div>
          <div className="eyebrow">Project</div>
          <h1>{project.name}</h1>
          <p>{project.description || "No description yet."}</p>
        </div>
        <div className="status-chip">{project.archived ? "Archived" : "Active"}</div>
      </header>

      <div className="overview-grid">
        <article className="panel">
          <span className="panel-label">Status</span>
          <strong>{project.archived ? "Archived" : "Active"}</strong>
        </article>
        <article className="panel">
          <span className="panel-label">Created</span>
          <strong>{new Date(project.created_at).toLocaleDateString()}</strong>
        </article>
        <article className="panel">
          <span className="panel-label">Last updated</span>
          <strong>{new Date(project.updated_at).toLocaleDateString()}</strong>
        </article>
      </div>

      <div className="workspace-placeholder">
        <div>
          <div className="eyebrow">Next</div>
          <h2>Ticket board</h2>
          <p>AD-6 will turn this project workspace into the Kanban board.</p>
        </div>
      </div>
    </section>
  );
}

export default App;
