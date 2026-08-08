import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type Project } from "./api/projects";
import {
  cloneRepository,
  createRepository,
  deleteRepository,
  listRepositories,
  updateRepository,
  type Repository,
  type RepositoryProvider,
} from "./api/repositories";

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
  const [draft, setDraft] = useState<RepositoryDraft>(emptyDraft);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    if (!projectId) return;
    const [nextProject, nextRepositories] = await Promise.all([
      getProject(projectId),
      listRepositories(projectId),
    ]);
    setProject(nextProject);
    setRepositories(nextRepositories);
  }

  useEffect(() => {
    setError(null);
    refresh().catch((cause: unknown) =>
      setError(cause instanceof Error ? cause.message : "Unable to load repositories"),
    );
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
          <p>Register remotes here. AgentDesk owns the local clone and future ticket workspaces.</p>
        </div>
      </header>

      {error && <div className="notice error-notice"><strong>Repository action failed.</strong><span>{error}</span></div>}

      <div className="repository-layout">
        <section className="repository-list">
          <div className="repository-section-heading"><h2>Repositories</h2><span>{repositories.length}</span></div>

          {repositories.length === 0 && <div className="repository-empty">No repositories registered yet.</div>}

          {repositories.map((repository) => (
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
                  <button type="button" onClick={() => startEdit(repository)}>Edit</button>
                  <button type="button" className="danger-button" onClick={() => void remove(repository)}>Delete</button>
                </div>
              </div>
              <dl className="repository-meta">
                <div><dt>Provider</dt><dd>{repository.provider}</dd></div>
                <div><dt>Default branch</dt><dd>{repository.default_branch}</dd></div>
                <div><dt>Managed clone</dt><dd>{repository.managed_path || "Not cloned"}</dd></div>
              </dl>
            </article>
          ))}
        </section>

        <form className="repository-form" onSubmit={submit}>
          <div className="repository-section-heading"><h2>{editingId ? "Edit repository" : "Add repository"}</h2></div>

          <label>Name<input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="agentdesk" /></label>
          <label>
            Provider
            <select value={draft.provider} onChange={(e) => setDraft({ ...draft, provider: e.target.value as RepositoryProvider })}>
              <option value="github">GitHub</option>
              <option value="gitlab">GitLab</option>
              <option value="other">Other Git remote</option>
            </select>
          </label>
          <label>Remote URL<input value={draft.remote_url} onChange={(e) => setDraft({ ...draft, remote_url: e.target.value })} placeholder="https://github.com/org/repo" /></label>
          <label>Default branch<input value={draft.default_branch} onChange={(e) => setDraft({ ...draft, default_branch: e.target.value })} /></label>
          <label className="repository-checkbox">
            <input type="checkbox" checked={draft.is_primary} onChange={(e) => setDraft({ ...draft, is_primary: e.target.checked })} />
            Primary repository for this project
          </label>

          <div className="repository-form-actions">
            {editingId && <button type="button" onClick={resetForm}>Cancel</button>}
            <button type="submit" className="primary-button" disabled={busyId === "form" || !draft.name.trim() || !draft.remote_url.trim()}>
              {busyId === "form" ? "Saving…" : editingId ? "Save changes" : "Add repository"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
