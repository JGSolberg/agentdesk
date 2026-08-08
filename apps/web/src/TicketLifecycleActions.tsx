import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteTicket, updateTicket, type Ticket } from "./api/tickets";
import type { Repository } from "./api/repositories";
import { adoptPullRequest, type Workspace } from "./api/workspaces";
import TicketRelationships from "./TicketRelationships";

type Pane = "menu" | "relationships" | "workspace" | "adopt" | "lifecycle";

type Props = {
  ticket: Ticket;
  onChanged: () => Promise<void>;
  onEdit: () => void;
  repositories: Repository[];
  activeWorkspaces: Workspace[];
  archivedWorkspaces: Workspace[];
  workspaceRepositoryId: string;
  workspaceBusy: boolean;
  onWorkspaceRepositoryChange: (repositoryId: string) => void;
  onCreateWorkspace: () => Promise<void>;
  onRemoveWorkspace: (workspace: Workspace) => Promise<void>;
};

export default function TicketLifecycleActions({ ticket, onChanged, onEdit, repositories, activeWorkspaces, archivedWorkspaces, workspaceRepositoryId, workspaceBusy, onWorkspaceRepositoryChange, onCreateWorkspace, onRemoveWorkspace }: Props) {
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [pane, setPane] = useState<Pane>("menu");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adoptRepositoryId, setAdoptRepositoryId] = useState("");
  const cloneReadyRepositories = repositories.filter((repository) => repository.managed_path);

  useEffect(() => {
    function close() { setOpen(false); setPane("menu"); }
    function onPointerDown(event: MouseEvent) { if (menuRef.current && !menuRef.current.contains(event.target as Node)) close(); }
    function onKeyDown(event: KeyboardEvent) { if (event.key === "Escape") close(); }
    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => { window.removeEventListener("mousedown", onPointerDown); window.removeEventListener("keydown", onKeyDown); };
  }, []);

  useEffect(() => {
    if (!adoptRepositoryId && cloneReadyRepositories.length > 0) setAdoptRepositoryId(cloneReadyRepositories.find((repository) => repository.is_primary)?.id ?? cloneReadyRepositories[0].id);
  }, [adoptRepositoryId, cloneReadyRepositories]);

  async function mutate(action: () => Promise<unknown>) {
    setBusy(true); setError(null);
    try { await action(); await onChanged(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Ticket lifecycle action failed"); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (!window.confirm(`Permanently delete ${ticket.ticket_key}? This cannot be undone.`)) return;
    setBusy(true); setError(null);
    try { await deleteTicket(ticket.id); navigate(`/projects/${ticket.project_id}`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to delete ticket"); setBusy(false); }
  }

  async function adopt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!adoptRepositoryId) return;
    const data = new FormData(event.currentTarget);
    const pullRequest = String(data.get("pull_request") ?? "").trim();
    if (!pullRequest) return;
    setBusy(true); setError(null);
    try {
      await adoptPullRequest(adoptRepositoryId, { ticket_id: ticket.id, pull_request: pullRequest });
      await onChanged();
      setPane("workspace");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to adopt existing work"); }
    finally { setBusy(false); }
  }

  function toggle() { setOpen((value) => { if (value) setPane("menu"); return !value; }); setError(null); }
  function edit() { setOpen(false); setPane("menu"); onEdit(); }
  const paneTitle = pane === "relationships" ? "Relationships" : pane === "workspace" ? "Workspace" : pane === "adopt" ? "Adopt existing work" : "Lifecycle";

  return (
    <div className="ticket-lifecycle-wrap">
      <div className="ticket-actions-menu" ref={menuRef}>
        <button className="ticket-actions-trigger" type="button" onClick={toggle} aria-expanded={open}>Actions <span>▾</span></button>
        {open && (
          <div className={`ticket-actions-popover${pane === "menu" ? "" : " expanded"}`}>
            {pane === "menu" ? (
              <>
                <button type="button" onClick={edit}><strong>Edit ticket</strong><span>Title, status, criteria, and details</span></button>
                <button type="button" onClick={() => setPane("relationships")}><strong>Relationships</strong><span>Parent, dependencies, blockers</span><b>›</b></button>
                <button type="button" onClick={() => setPane("workspace")}><strong>Workspace</strong><span>{activeWorkspaces.length ? `${activeWorkspaces.length} active worktree${activeWorkspaces.length === 1 ? "" : "s"}` : "Create or reactivate a worktree"}</span><b>›</b></button>
                <button type="button" onClick={() => setPane("adopt")} disabled={activeWorkspaces.length > 0}><strong>Adopt existing work</strong><span>{activeWorkspaces.length ? "Remove the current workspace first" : "Attach an existing GitHub pull request"}</span><b>›</b></button>
                <button type="button" onClick={() => setPane("lifecycle")}><strong>Lifecycle</strong><span>Cancel, archive, or delete</span><b>›</b></button>
              </>
            ) : (
              <>
                <header className="ticket-actions-panel-header"><button type="button" className="ticket-actions-back" onClick={() => setPane("menu")}>← Back</button><div><span>{ticket.ticket_key}</span><strong>{paneTitle}</strong></div></header>
                <div className="ticket-actions-panel-body">
                  {pane === "relationships" && <TicketRelationships ticket={ticket} onChanged={onChanged} />}
                  {pane === "workspace" && (
                    <div className="lifecycle-menu-content">
                      {activeWorkspaces.map((workspace) => { const repository = repositories.find((item) => item.id === workspace.repository_id); return <div className="workspace-action-item" key={workspace.id}><div><strong>{workspace.branch}</strong><span>{repository?.name ?? "Repository"}</span><code>{workspace.path}</code></div><button type="button" disabled={workspaceBusy} onClick={() => void onRemoveWorkspace(workspace)}>Remove worktree</button></div>; })}
                      {activeWorkspaces.length === 0 && cloneReadyRepositories.length > 0 && <><p>{archivedWorkspaces.length ? "Recreate the ticket workspace on its existing branch, create a new one, or adopt an existing PR from the Actions menu." : "Create an AgentDesk-owned worktree for this ticket, or adopt an existing PR from the Actions menu."}</p><div className="ticket-workspace-create"><select value={workspaceRepositoryId} onChange={(event) => onWorkspaceRepositoryChange(event.target.value)}>{cloneReadyRepositories.map((repository) => <option key={repository.id} value={repository.id}>{repository.name}</option>)}</select><button type="button" disabled={workspaceBusy || !workspaceRepositoryId} onClick={() => void onCreateWorkspace()}>{workspaceBusy ? "Creating…" : archivedWorkspaces.length ? "Reactivate workspace" : "Create workspace"}</button></div></>}
                      {activeWorkspaces.length === 0 && cloneReadyRepositories.length === 0 && repositories.length > 0 && <p>Clone a project repository before creating or adopting a workspace.</p>}
                      {repositories.length === 0 && <p>Register a repository for this project before creating a workspace.</p>}
                      {archivedWorkspaces.length > 0 && <div className="workspace-action-archive"><strong>Archived</strong>{archivedWorkspaces.map((workspace) => <span key={workspace.id}>{workspace.branch}</span>)}</div>}
                    </div>
                  )}
                  {pane === "adopt" && (
                    <form className="adopt-work-form" onSubmit={adopt}>
                      <p>Attach this ticket to work that already exists in GitHub. AgentDesk will fetch the PR head branch and create its managed worktree from that branch.</p>
                      {cloneReadyRepositories.length > 0 ? <><label>Repository<select value={adoptRepositoryId} onChange={(event) => setAdoptRepositoryId(event.target.value)}>{cloneReadyRepositories.map((repository) => <option key={repository.id} value={repository.id}>{repository.name}</option>)}</select></label><label>Pull request<input name="pull_request" required placeholder="33 or https://github.com/owner/repo/pull/33" /></label><div className="adopt-work-actions"><button type="button" onClick={() => setPane("menu")}>Cancel</button><button className="primary" type="submit" disabled={busy}>{busy ? "Adopting…" : "Adopt pull request"}</button></div></> : <p>Clone a project repository before adopting existing work.</p>}
                      {error && <span className="ticket-lifecycle-error">{error}</span>}
                    </form>
                  )}
                  {pane === "lifecycle" && (
                    <div className="lifecycle-menu-content"><p>Cancel keeps the ticket visible. Archive hides it from the board. Delete permanently removes disposable tickets.</p><div className="ticket-lifecycle-actions"><button type="button" disabled={busy || ticket.archived} onClick={() => void mutate(() => updateTicket(ticket.id, { status: ticket.status === "cancelled" ? "backlog" : "cancelled" }))}>{ticket.status === "cancelled" ? "Reopen" : "Cancel ticket"}</button><button type="button" disabled={busy} onClick={() => void mutate(() => updateTicket(ticket.id, { archived: !ticket.archived }))}>{ticket.archived ? "Unarchive" : "Archive"}</button><button type="button" className="danger-button" disabled={busy} onClick={() => void remove()}>Delete permanently</button></div>{ticket.archived && <span className="ticket-lifecycle-note">Archived tickets remain searchable.</span>}{error && <span className="ticket-lifecycle-error">{error}</span>}</div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
