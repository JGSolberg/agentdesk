import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject, type Project } from "./api/projects";
import {
  createRepository,
  deleteRepository,
  listRepositories,
  updateRepository,
  type Repository,
  type RepositoryProvider,
} from "./api/repositories";

type RepositoryDraft = {
  name: string;
  local_path: string;
  provider: RepositoryProvider;
  remote_url: string;
  default_branch: string;
  is_primary: boolean;
};

const emptyDraft: RepositoryDraft = {
  name: "",
  local_path: "",
  provider: "local",
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
  const [busy, setBusy] = useState(false);

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
      local_path: repository.local_path,
      provider: repository.provider,
      remote_url: repository.remote_url ?? "",
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
    if (!projectId || !draft.name.trim() || !draft.local_path.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const payload = {
        name: draft.name.trim(),
        local_path: draft.local_path.trim(),
        provider: draft.provider,
        remote_url: draft.remote_url.trim() || null,
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
      setBusy(false);
    }
  }

  async function remove(repository: Repository) {
    if (!window.confirm(`Delete repository registration “${repository.name}”? This does not delete files from disk.`)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteRepository(repository.id);
      if (editingId === repository.id) resetForm();
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete repository");
    } finally {
      setBusy(false);
    }
  }

  if (!project && !error) return <section className="page loading-page">Loading repositories…</section>;

  return (
    <section className="page repository-page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Project repositories</div>
          <h1>{project?.name ?? "Repositories"}</h1>
          <p>Register the local codebases AgentDesk should know about for this project.</p>
        </div>
      </header>

      {error && <div className="notice error-notice"><strong>Repository action failed.</strong><span>{error}</span></div>}

      <div className="repository-layout">
        <section className="repository-list">
          <div className="repository-section-heading">
            <h2>Registered repositories</h2>
            <span>{repositories.length}</span>
          </div>

          {repositories.length === 0 && (
            <div className="repository-empty">No repositories registered yet.</div>
          )}

          {repositories.map((repository) => (
            <article className="repository-card" key={repository.id}>
              <div className="repository-card-header">
                <div>
                  <div className="repository-title-row">
                    <h3>{repository.name}</h3>
                    {repository.is_primary && <span className="repository-primary">Primary</span>}
                  </div>
                  <code>{repository.local_path}</code>
                </div>
                <div className="repository-actions">
                  <button type="button" onClick={() => startEdit(repository)}>Edit</button>
                  <button type="button" className="danger-button" onClick={() => void remove(repository)}>Delete</button>
                </div>
              </div>
              <dl className="repository-meta">
                <div><dt>Provider</dt><dd>{repository.provider}</dd></div>
                <div><dt>Default branch</dt><dd>{repository.default_branch}</dd></div>
                <div><dt>Remote</dt><dd>{repository.remote_url || "Not set"}</dd></div>
              </dl>
            </article>
          ))}
        </section>

        <form className="repository-form" onSubmit={submit}>
          <div className="repository-section-heading">
            <h2>{editingId ? "Edit repository" : "Add repository"}</h2>
          </div>

          <label>
            Name
            <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="agentdesk" />
          </label>
          <label>
            Local path
            <input value={draft.local_path} onChange={(e) => setDraft({ ...draft, local_path: e.target.value })} placeholder="E:\\Coding\\agentdesk" />
          </label>
          <label>
            Provider
            <select value={draft.provider} onChange={(e) => setDraft({ ...draft, provider: e.target.value as RepositoryProvider })}>
              <option value="local">Local</option>
              <option value="github">GitHub</option>
              <option value="gitlab">GitLab</option>
            </select>
          </label>
          <label>
            Remote URL
            <input value={draft.remote_url} onChange={(e) => setDraft({ ...draft, remote_url: e.target.value })} placeholder="https://github.com/..." />
          </label>
          <label>
            Default branch
            <input value={draft.default_branch} onChange={(e) => setDraft({ ...draft, default_branch: e.target.value })} />
          </label>
          <label className="repository-checkbox">
            <input type="checkbox" checked={draft.is_primary} onChange={(e) => setDraft({ ...draft, is_primary: e.target.checked })} />
            Primary repository for this project
          </label>

          <div className="repository-form-actions">
            {editingId && <button type="button" onClick={resetForm}>Cancel</button>}
            <button type="submit" className="primary-button" disabled={busy || !draft.name.trim() || !draft.local_path.trim()}>
              {busy ? "Saving…" : editingId ? "Save changes" : "Add repository"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
