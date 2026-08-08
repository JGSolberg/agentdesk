import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type Project } from "./api/projects";
import {
  cloneRepository,
  createRepository,
  deleteRepository,
  listRepositories,
  removeManagedClone,
  updateRepository,
  type Repository,
  type RepositoryProvider,
} from "./api/repositories";
import { listTickets, type Ticket } from "./api/tickets";
import { createWorkspace, listWorkspaces, removeWorkspace, type Workspace } from "./api/workspaces";

type RepositoryDraft = {
  name: string;
  provider: RepositoryProvider;
  remote_url: string;
  default_branch: string;
  is_primary: boolean;
};

const emptyDraft: RepositoryDraft = {
  name: "",
  provider: "github",
  remote_url: "",
  default_branch: "main",
  is_primary: false,
};

export default function RepositoryPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [workspaces, setWorkspaces] = useState<Record<string, Workspace[]>>({});
  const [draft, setDraft] = useState<RepositoryDraft>(emptyDraft);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [workspaceTicket, setWorkspaceTicket] = useState<Record<string, string>>({});
  const [workspaceBranch, setWorkspaceBranch] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    if (!projectId) return;
    const [nextProject, nextRepositories, nextTickets] = await Promise.all([
      getProject(projectId),
      listRepositories(projectId),
      listTickets(projectId),
    ]);
    setProject(nextProject);
    setRepositories(nextRepositories);
    setTickets(nextTickets);
    const entries = await Promise.all(nextRepositories.map(async (repository) => [repository.id, await listWorkspaces(repository.id)] as const));
    setWorkspaces(Object.fromEntries(entries));
  }

  useEffect(() => {
    setError(null);
    refresh().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load repositories"));
  }, [projectId]);

  function startEdit(repository: Repository) {
    setEditingId(repository.id);
    setDraft({
      name: repository.name,
      provider: repository.provider,
      remote_url: repository.remote_url,
      default_branch: repository.default_branch,
      is_primary: repository.is_primary,
    });
  }

  function resetForm() {
    setEditingId(null);
    setDraft(emptyDraft);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!projectId || !draft.name.trim() || !draft.remote_url.trim()) return;
    setBusyId("form");
    setError(null);
    try {
      const payload = {
        name: draft.name.trim(),
        provider: draft.provider,
        remote_url: draft.remote_url.trim(),
        default_branch: draft.default_branch.trim() || "main",
        is_primary: draft.is_primary,
      };
      if (editingId) await updateRepository(editingId, payload);
      else await createRepository(projectId, payload);
      resetForm();
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save repository");
    } finally {
      setBusyId(null);
    }
  }

  async function clone(repository: Repository) {
    setBusyId(repository.id);
    setError(null);
    try {
      await cloneRepository(repository.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to clone repository");
    } finally {
      setBusyId(null);
    }
  }

  async function addWorkspace(repository: Repository) {
    const ticketId = workspaceTicket[repository.id] || null;
    const branch = workspaceBranch[repository.id]?.trim() || null;
    if (!ticketId && !branch) {
      setError("Choose a ticket or enter a branch name for the workspace.");
      return;
    }
    setBusyId(`workspace-${repository.id}`);
    setError(null);
    try {
      await createWorkspace(repository.id, { ticket_id: ticketId, branch });
      setWorkspaceTicket((current) => ({ ...current, [repository.id]: "" }));
      setWorkspaceBranch((current) => ({ ...current, [repository.id]: "" }));
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create workspace");
    } finally {
      setBusyId(null);
    }
  }

  async function dropWorkspace(workspace: Workspace) {
    if (!window.confirm(`Remove workspace “${workspace.name}”? The branch is retained in Git.`)) return;
    setBusyId(`workspace-${workspace.id}`);
    setError(null);
    try {
      await removeWorkspace(workspace.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to remove workspace");
    } finally {
      setBusyId(null);
    }
  }

  async function removeClone(repository: Repository) {
    if (!window.confirm(`Remove AgentDesk's managed clone for “${repository.name}”?`)) return;
    setBusyId(repository.id);
    setError(null);
    try {
      await removeManagedClone(repository.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to remove managed clone");
    } finally {
      setBusyId(null);
    }
  }

  async function remove(repository: Repository) {
    if (!window.confirm(`Delete repository registration “${repository.name}”?`)) return;
    setBusyId(repository.id);
    setError(null);
    try {
      await deleteRepository(repository.id);
      if (editingId === repository.id) resetForm();
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete repository");
    } finally {
      setBusyId(null);
    }
  }

  if (!project && !error) return <section className="page loading-page">Loading repositories…</section>;

  return (
    <section className="page repository-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Project repositories</div>
          <h1>{project?.name ?? "Repositories"}</h1>
          <p>AgentDesk owns the canonical clone and isolated Git worktrees used for ticket work.</p>
        </div>
      </header>

      {error && <div className="notice error-notice"><strong>Repository action failed.</strong><span>{error}</span></div>}

      <div className="repository-layout">
        <section className="repository-list">
          <div className="repository-section-heading"><h2>Repositories</h2><span>{repositories.length}</span></div>
          {repositories.length === 0 && <div className="repository-empty">No repositories registered yet.</div>}

          {repositories.map((repository) => {
            const repositoryWorkspaces = workspaces[repository.id] ?? [];
            const activeWorkspaces = repositoryWorkspaces.filter((workspace) => workspace.status === "active");
            return (
              <article className="repository-card" key={repository.id}>
                <div className="repository-card-header">
                  <div>
                    <div className="repository-title-row">
                      <h3>{repository.name}</h3>
                      {repository.is_primary && <span className="repository-primary">Primary</span>}
                    </div>
                    <code>{repository.remote_url}</code>
                  </div>
                  <div className="repository-actions">
                    <button type="button" onClick={() => void clone(repository)} disabled={busyId === repository.id}>
                      {busyId === repository.id ? "Working…" : repository.managed_path ? "Refresh clone" : "Clone"}
                    </button>
                    {repository.managed_path && <button type="button" onClick={() => void removeClone(repository)} disabled={busyId === repository.id}>Remove clone</button>}
                    <button type="button" onClick={() => startEdit(repository)}>Edit</button>
                    <button type="button" className="danger-button" onClick={() => void remove(repository)}>Delete</button>
                  </div>
                </div>
                <dl className="repository-meta">
                  <div><dt>Provider</dt><dd>{repository.provider}</dd></div>
                  <div><dt>Default branch</dt><dd>{repository.default_branch}</dd></div>
                  <div><dt>Managed clone</dt><dd>{repository.managed_path || "Not cloned"}</dd></div>
                </dl>

                {repository.managed_path && (
                  <section className="workspace-panel">
                    <div className="repository-section-heading"><h4>Workspaces</h4><span>{activeWorkspaces.length}</span></div>
                    <div className="workspace-create-row">
                      <select value={workspaceTicket[repository.id] ?? ""} onChange={(e) => setWorkspaceTicket((current) => ({ ...current, [repository.id]: e.target.value }))}>
                        <option value="">No ticket</option>
                        {tickets.filter((ticket) => ticket.type !== "epic").map((ticket) => <option value={ticket.id} key={ticket.id}>{ticket.ticket_key} — {ticket.title}</option>)}
                      </select>
                      <input value={workspaceBranch[repository.id] ?? ""} onChange={(e) => setWorkspaceBranch((current) => ({ ...current, [repository.id]: e.target.value }))} placeholder="Branch override (optional for ticket)" />
                      <button type="button" onClick={() => void addWorkspace(repository)} disabled={busyId === `workspace-${repository.id}`}>{busyId === `workspace-${repository.id}` ? "Creating…" : "Create workspace"}</button>
                    </div>
                    <div className="workspace-list">
                      {activeWorkspaces.length === 0 && <span className="repository-empty">No active workspaces.</span>}
                      {activeWorkspaces.map((workspace) => (
                        <div className="workspace-row" key={workspace.id}>
                          <div><strong>{workspace.name}</strong><code>{workspace.branch}</code><span>{workspace.path}</span></div>
                          <button type="button" onClick={() => void dropWorkspace(workspace)} disabled={busyId === `workspace-${workspace.id}`}>Remove</button>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </article>
            );
          })}
        </section>

        <form className="repository-form" onSubmit={submit}>
          <div className="repository-section-heading"><h2>{editingId ? "Edit repository" : "Add repository"}</h2></div>
          <label>Name<input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="agentdesk" /></label>
          <label>Provider<select value={draft.provider} onChange={(e) => setDraft({ ...draft, provider: e.target.value as RepositoryProvider })}><option value="github">GitHub</option><option value="gitlab">GitLab</option><option value="other">Other Git remote</option></select></label>
          <label>Remote URL<input value={draft.remote_url} onChange={(e) => setDraft({ ...draft, remote_url: e.target.value })} placeholder="https://github.com/org/repo" /></label>
          <label>Default branch<input value={draft.default_branch} onChange={(e) => setDraft({ ...draft, default_branch: e.target.value })} /></label>
          <label className="repository-checkbox"><input type="checkbox" checked={draft.is_primary} onChange={(e) => setDraft({ ...draft, is_primary: e.target.checked })} />Primary repository for this project</label>
          <div className="repository-form-actions">
            {editingId && <button type="button" onClick={resetForm}>Cancel</button>}
            <button type="submit" className="primary-button" disabled={busyId === "form" || !draft.name.trim() || !draft.remote_url.trim()}>{busyId === "form" ? "Saving…" : editingId ? "Save changes" : "Add repository"}</button>
          </div>
        </form>
      </div>
    </section>
  );
}
