import { useEffect, useState } from "react";

import { getWorkspaceStatus, type Workspace, type WorkspaceGitStatus } from "./api/workspaces";

export default function WorkspaceStatusCard({ workspace }: { workspace: Workspace }) {
  const [status, setStatus] = useState<WorkspaceGitStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setStatus(await getWorkspaceStatus(workspace.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to inspect workspace");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, [workspace.id]);

  return (
    <div className="workspace-status-card">
      <div className="workspace-status-topline">
        <strong>{loading ? "Inspecting…" : status?.clean ? "Clean" : "Changes present"}</strong>
        <button type="button" onClick={() => void refresh()} disabled={loading}>Refresh</button>
      </div>
      {error && <span className="workspace-status-error">{error}</span>}
      {status && (
        <>
          <div className="workspace-status-grid">
            <span>Staged <b>{status.staged}</b></span>
            <span>Modified <b>{status.modified}</b></span>
            <span>Untracked <b>{status.untracked}</b></span>
            <span>Ahead <b>{status.ahead ?? "—"}</b></span>
            <span>Behind <b>{status.behind ?? "—"}</b></span>
          </div>
          <div className="workspace-head"><code>{status.head_sha}</code><span>{status.head_message}</span></div>
        </>
      )}
    </div>
  );
}
