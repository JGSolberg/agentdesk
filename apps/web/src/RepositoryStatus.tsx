import { useEffect, useState } from "react";

import { getRepositoryStatus, type GitRepositoryStatus } from "./api/repositories";
import "./repository-status.css";

export default function RepositoryStatus({ repositoryId }: { repositoryId: string }) {
  const [status, setStatus] = useState<GitRepositoryStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setStatus(await getRepositoryStatus(repositoryId));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to inspect repository");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [repositoryId]);

  if (loading) return <div className="git-status-card muted">Inspecting Git repository…</div>;
  if (error) return <div className="git-status-card invalid">{error}</div>;
  if (!status) return null;

  if (!status.path_exists || !status.is_git_repository) {
    return (
      <div className="git-status-card invalid">
        <div className="git-status-heading">Repository status</div>
        <strong>{status.error ?? "Git repository unavailable"}</strong>
        <button type="button" onClick={() => void refresh()}>Refresh</button>
      </div>
    );
  }

  return (
    <div className="git-status-card">
      <div className="git-status-topline">
        <div>
          <div className="git-status-heading">Repository status</div>
          <strong>{status.is_dirty ? "Working tree has changes" : "Working tree clean"}</strong>
        </div>
        <button type="button" onClick={() => void refresh()}>Refresh</button>
      </div>

      <dl className="git-status-grid">
        <div><dt>Branch</dt><dd>{status.branch ?? "Detached HEAD"}</dd></div>
        <div><dt>Staged</dt><dd>{status.staged_count}</dd></div>
        <div><dt>Modified</dt><dd>{status.modified_count}</dd></div>
        <div><dt>Untracked</dt><dd>{status.untracked_count}</dd></div>
      </dl>

      <div className="git-status-detail">
        <span>Origin</span>
        <code>{status.remote_url ?? "No origin remote"}</code>
      </div>
      <div className="git-status-detail">
        <span>HEAD</span>
        <code>{status.head_sha ? status.head_sha.slice(0, 10) : "No commits"}</code>
        {status.head_message && <small>{status.head_message}</small>}
      </div>
      {status.error && <p className="git-status-warning">{status.error}</p>}
    </div>
  );
}
