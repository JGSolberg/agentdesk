const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export type Agent = {
  id: string;
  project_id: string;
  name: string;
  provider: string;
  model: string | null;
  command: string | null;
  capabilities: string[];
  enabled: boolean;
};

export type RunStatus = "queued" | "running" | "needs_human" | "succeeded" | "failed" | "cancelled";

export type AgentRun = {
  id: string;
  ticket_id: string;
  agent_id: string;
  workspace_id: string | null;
  status: RunStatus;
  context_snapshot: Record<string, unknown>;
  logs: Array<{ timestamp: string; level: string; message: string }>;
  result: string | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options });
  if (!response.ok) {
    let detail = `AgentDesk API request failed (${response.status})`;
    try { const body = await response.json() as { detail?: string }; if (body.detail) detail = body.detail; } catch { /* use fallback */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function listAgents(projectId: string): Promise<Agent[]> { return request(`/projects/${projectId}/agents`); }
export function createAgent(projectId: string, payload: { name: string; provider: string; command: string; capabilities?: string[] }): Promise<Agent> { return request(`/projects/${projectId}/agents`, { method: "POST", body: JSON.stringify(payload) }); }
export function listRuns(ticketId: string): Promise<AgentRun[]> { return request(`/tickets/${ticketId}/runs`); }
export function createRun(ticketId: string, payload: { agent_id: string; workspace_id: string }): Promise<AgentRun> { return request(`/tickets/${ticketId}/runs`, { method: "POST", body: JSON.stringify(payload) }); }
export function executeRun(runId: string): Promise<AgentRun> { return request(`/runs/${runId}/execute`, { method: "POST" }); }
