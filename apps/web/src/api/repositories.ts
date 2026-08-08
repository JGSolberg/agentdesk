export type RepositoryProvider = "github" | "gitlab" | "other";

export type Repository = {
  id: string;
  project_id: string;
  name: string;
  provider: RepositoryProvider;
  remote_url: string;
  default_branch: string;
  managed_path: string | null;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
};

const API_URL = import.meta.env.VITE_API_URL ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `AgentDesk API request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep status fallback when the API does not return JSON.
    }
    throw new Error(detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function listRepositories(projectId: string): Promise<Repository[]> {
  return request<Repository[]>(`/projects/${projectId}/repositories`);
}

export function createRepository(
  projectId: string,
  payload: {
    name: string;
    provider: RepositoryProvider;
    remote_url: string;
    default_branch: string;
    is_primary?: boolean;
  },
): Promise<Repository> {
  return request<Repository>(`/projects/${projectId}/repositories`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateRepository(
  repositoryId: string,
  payload: Partial<Pick<Repository, "name" | "provider" | "remote_url" | "default_branch" | "is_primary">>,
): Promise<Repository> {
  return request<Repository>(`/repositories/${repositoryId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function cloneRepository(repositoryId: string): Promise<Repository> {
  return request<Repository>(`/repositories/${repositoryId}/clone`, { method: "POST" });
}

export function removeManagedClone(repositoryId: string): Promise<Repository> {
  return request<Repository>(`/repositories/${repositoryId}/clone`, { method: "DELETE" });
}

export function deleteRepository(repositoryId: string): Promise<void> {
  return request<void>(`/repositories/${repositoryId}`, { method: "DELETE" });
}
