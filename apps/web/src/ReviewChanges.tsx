import { useEffect, useState } from "react";

import { updateTicket, type TicketStatus } from "./api/tickets";
import { getWorkspaceReview, publishWorkspace, type Workspace, type WorkspacePublishResult, type WorkspaceReview } from "./api/workspaces";

export default function ReviewChanges({ ticketId, ticketStatus, workspace }: { ticketId: string; ticketStatus: TicketStatus; workspace: Workspace }) {
  const [review, setReview] = useState<WorkspaceReview | null>(null);
  const [published, setPublished] = useState<WorkspacePublishResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    const next = await getWorkspaceReview(workspace.id);
    setReview(next);
  }

  useEffect(() => {
    setReview(null);
    setPublished(null);
    setError(null);
    void reload().catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load workspace changes"));
  }, [workspace.id]);

  async function createPullRequest() {
    setBusy(true);
    setError(null);
    try {
      const result = await publishWorkspace(workspace.id);
      setPublished(result);
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create pull request");
    } finally {
      setBusy(false);
    }
  }

  async function requestChanges() {
    setBusy(true);
    setError(null);
    try {
      await updateTicket(ticketId, { status: "in_progress" });
      window.location.reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to request changes");
      setBusy(false);
    }
  }

  if (!review && !error) return <div className="review-changes"><h3>Review changes</h3><p className="detail-empty">Loading worktree diff…</p></div>;

  const prUrl = published?.pull_request_url ?? review?.pull_request_url ?? null;
  const prNumber = published?.pull_request_number ?? review?.pull_request_number ?? null;

  return <div className="review-changes">
    <div className="review-heading">
      <div>
        <h3>Review changes</h3>
        <p>Inspect the agent work here. GitHub remains the merge and approval authority.</p>
      </div>
      {review && !review.clean && <span className="review-summary">{review.files.length} file{review.files.length === 1 ? "" : "s"} · +{review.additions} / -{review.deletions}</span>}
    </div>

    {prUrl && <div className="review-pr-ready"><strong>{published?.created ? "Pull request created" : "Pull request ready for review"}</strong><a href={prUrl} target="_blank" rel="noreferrer">Open PR{prNumber ? ` #${prNumber}` : ""} in GitHub ↗</a></div>}
    {error && <p className="ticket-lifecycle-error">{error}</p>}

    {review?.clean && !prUrl && <p className="detail-empty">No uncommitted reviewable changes in this workspace.</p>}

    {review && !review.clean && <>
      <div className="review-file-list">{review.files.map((file) => <div key={`${file.status}-${file.path}`}><code>{file.status}</code><span>{file.path}</span></div>)}</div>
      <details className="review-diff" open={ticketStatus === "review"}>
        <summary>View diff</summary>
        <pre>{review.diff || "No textual diff available."}</pre>
      </details>
      <div className="review-actions">
        <button type="button" disabled={busy} onClick={() => void requestChanges()}>Request changes</button>
        {!prUrl && <button className="primary" type="button" disabled={busy} onClick={() => void createPullRequest()}>{busy ? "Working…" : "Create PR"}</button>}
      </div>
    </>}
  </div>;
}
