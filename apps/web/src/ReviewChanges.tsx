import { useEffect, useState } from "react";

import { updateTicket, type Ticket } from "./api/tickets";
import { getWorkspaceReview, publishWorkspace, syncWorkspacePr, type Workspace, type WorkspacePublishResult, type WorkspaceReview } from "./api/workspaces";

export default function ReviewChanges({ ticket, workspace, onChanged }: { ticket: Ticket; workspace: Workspace; onChanged: () => Promise<void> | void }) {
  const [review, setReview] = useState<WorkspaceReview | null>(null);
  const [published, setPublished] = useState<WorkspacePublishResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reload() { setReview(await getWorkspaceReview(workspace.id)); }

  useEffect(() => {
    setReview(null); setPublished(null); setError(null);
    void reload().catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load workspace changes"));
  }, [workspace.id]);

  async function publish() {
    setBusy(true); setError(null);
    try {
      const result = await publishWorkspace(workspace.id);
      setPublished(result);
      await reload();
      await onChanged();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to publish workspace"); }
    finally { setBusy(false); }
  }

  async function syncPullRequest() {
    setBusy(true); setError(null);
    try {
      const result = await syncWorkspacePr(workspace.id);
      if (result.merged && result.cleaned_up) { await onChanged(); return; }
      if (!result.found) setError("No pull request found for this branch yet.");
      else setError(`Pull request is still ${result.state ?? "open"}. Merge it in GitHub, then sync again.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to sync pull request status"); }
    finally { setBusy(false); }
  }

  async function requestChanges() {
    setBusy(true); setError(null);
    try { await updateTicket(ticket.id, { status: "in_progress" }); await onChanged(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to request changes"); }
    finally { setBusy(false); }
  }

  if (!review && !error) return <section className="detail-section review-changes"><h2>Review changes</h2><p className="detail-empty">Loading worktree diff…</p></section>;

  const prUrl = published?.pull_request_url ?? review?.pull_request_url ?? null;
  const prNumber = published?.pull_request_number ?? review?.pull_request_number ?? null;

  return <section className="detail-section review-changes">
    <div className="review-heading"><div><h2>Review changes</h2><p>Inspect the agent work here. GitHub remains the merge and approval authority.</p></div>{review && !review.clean && <span className="review-summary">{review.files.length} file{review.files.length === 1 ? "" : "s"} · +{review.additions} / -{review.deletions}</span>}</div>

    {prUrl && <div className="review-pr-ready">
      <div><strong>{published?.created ? "Pull request created" : review?.unpublished ? "Pull request has unpublished updates" : "Pull request ready"}</strong><span>{workspace.branch}{prNumber ? ` · PR #${prNumber}` : ""}</span></div>
      <a className="review-pr-link" href={prUrl} target="_blank" rel="noreferrer">Open PR{prNumber ? ` #${prNumber}` : ""} in GitHub ↗</a>
    </div>}
    {error && <p className="ticket-lifecycle-error">{error}</p>}
    {review?.clean && !prUrl && <p className="detail-empty">No reviewable changes in this workspace.</p>}

    {review && !review.clean && <><div className="review-file-list">{review.files.map((file) => <div key={`${file.status}-${file.path}`}><code>{file.status}</code><span>{file.path}</span></div>)}</div><details className="review-diff" open={ticket.status === "review"}><summary>View diff</summary><pre>{review.diff || "No textual diff available."}</pre></details></>}

    <div className="review-actions">
      {review && !review.clean && <button type="button" disabled={busy} onClick={() => void requestChanges()}>Request changes</button>}
      {!prUrl && review && !review.clean && <button className="primary" type="button" disabled={busy} onClick={() => void publish()}>{busy ? "Creating PR…" : "Create PR"}</button>}
      {prUrl && review?.unpublished && <button className="primary" type="button" disabled={busy} onClick={() => void publish()}>{busy ? "Updating PR…" : `Update PR${prNumber ? ` #${prNumber}` : ""}`}</button>}
      {prUrl && !review?.unpublished && <button className="primary" type="button" disabled={busy} onClick={() => void syncPullRequest()}>{busy ? "Checking…" : "Sync PR status"}</button>}
    </div>
  </section>;
}
