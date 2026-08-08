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

const API_URL = import.meta.env.VITE_API_URL ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    let detail = `AgentDesk API request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep status fallback.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function listWorkspaces(repositoryId: string): Promise<Workspace[]> {
  return request<Workspace[]>(`/repositories/${repositoryId}/workspaces`);
}

export function createWorkspace(
  repositoryId: string,
  payload: { ticket_id?: string | null; name?: string | null; branch?: string | null },
): Promise<Workspace> {
  return request<Workspace>(`/repositories/${repositoryId}/workspaces`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function removeWorkspace(workspaceId: string): Promise<Workspace> {
  return request<Workspace>(`/workspaces/${workspaceId}`, { method: "DELETE" });
}
