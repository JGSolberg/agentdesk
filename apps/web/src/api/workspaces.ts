export type WorkspaceStatus = "active" | "removed";

export type Workspace = {
  id: string;
  project_id: string;
  repository_id: string;
  ticket_id: string | null;
  name: string;
  branch: string;
  path: string;
  status: WorkspaceStatus;
  created_at: string;
  updated_at: string;
};

export type WorkspaceGitStatus = {
  branch: string;
  clean: boolean;
  staged: number;
  modified: number;
  untracked: number;
  ahead: number | null;
  behind: number | null;
  head_sha: string;
  head_message: string;
};

export type WorkspaceReviewFile = { path: string; status: string };
export type WorkspaceReview = { workspace_id: string; branch: string; clean: boolean; unpublished: boolean; files: WorkspaceReviewFile[]; additions: number; deletions: number; diff: string; pull_request_url: string | null; pull_request_number: number | null; pull_request_merged: boolean };
export type WorkspacePublishResult = { branch: string; commit_sha: string | null; pull_request_url: string; pull_request_number: number | null; created: boolean };
export type WorkspacePrSync = { found: boolean; merged: boolean; cleaned_up: boolean; url?: string; number?: number | null; state?: string };

const API_URL = import.meta.env.VITE_API_URL ?? "/api";
async function request<T>(path: string, options?: RequestInit): Promise<T> { const response = await fetch(`${API_URL}${path}`, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options }); if (!response.ok) { let detail = `AgentDesk API request failed (${response.status})`; try { const body = (await response.json()) as { detail?: string }; if (body.detail) detail = body.detail; } catch {} throw new Error(detail); } return response.json() as Promise<T>; }

export function listWorkspaces(repositoryId: string): Promise<Workspace[]> { return request<Workspace[]>(`/repositories/${repositoryId}/workspaces`); }
export function createWorkspace(repositoryId: string, payload: { ticket_id?: string | null; name?: string | null; branch?: string | null }): Promise<Workspace> { return request<Workspace>(`/repositories/${repositoryId}/workspaces`, { method: "POST", body: JSON.stringify(payload) }); }
export function adoptPullRequest(repositoryId: string, payload: { ticket_id: string; pull_request: string }): Promise<Workspace> { return request<Workspace>(`/repositories/${repositoryId}/workspaces/adopt-pr`, { method: "POST", body: JSON.stringify(payload) }); }
export function getWorkspaceStatus(workspaceId: string): Promise<WorkspaceGitStatus> { return request<WorkspaceGitStatus>(`/workspaces/${workspaceId}/status`); }
export function getWorkspaceReview(workspaceId: string): Promise<WorkspaceReview> { return request<WorkspaceReview>(`/workspaces/${workspaceId}/review`); }
export function publishWorkspace(workspaceId: string): Promise<WorkspacePublishResult> { return request<WorkspacePublishResult>(`/workspaces/${workspaceId}/publish`, { method: "POST" }); }
export function syncWorkspacePr(workspaceId: string): Promise<WorkspacePrSync> { return request<WorkspacePrSync>(`/workspaces/${workspaceId}/sync-pr`, { method: "POST" }); }
export function removeWorkspace(workspaceId: string): Promise<Workspace> { return request<Workspace>(`/workspaces/${workspaceId}`, { method: "DELETE" }); }