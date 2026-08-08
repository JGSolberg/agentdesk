export type TicketStatus =
  | "backlog"
  | "ready"
  | "in_progress"
  | "review"
  | "done"
  | "blocked"
  | "needs_human"
  | "agent_failed";

export type TicketType = "epic" | "story" | "task" | "bug" | "spike";
export type TicketPriority = "low" | "medium" | "high" | "critical";

export type Ticket = {
  id: string;
  project_id: string;
  parent_id: string | null;
  sequence: number;
  ticket_key: string;
  type: TicketType;
  status: TicketStatus;
  priority: TicketPriority;
  title: string;
  description: string | null;
  goal: string | null;
  acceptance_criteria: string[];
  constraints: string[];
  definition_of_done: string[];
  relevant_files: string[];
  context: string[];
  estimated_complexity: string | null;
  requires_human: boolean;
  order: number;
  dependency_ids: string[];
  blocked_by_ids: string[];
  is_blocked: boolean;
  ready_to_start: boolean;
  created_at: string;
  updated_at: string;
  assignee?: string | null;
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
      // Keep the status-based fallback when no JSON body is available.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function listTickets(projectId: string): Promise<Ticket[]> {
  return request<Ticket[]>(`/projects/${projectId}/tickets`);
}

export function getTicket(ticketId: string): Promise<Ticket> {
  return request<Ticket>(`/tickets/${ticketId}`);
}

export function createTicket(
  projectId: string,
  payload: { title: string; type: TicketType; priority: TicketPriority; status?: TicketStatus },
): Promise<Ticket> {
  return request<Ticket>(`/projects/${projectId}/tickets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateTicket(
  ticketId: string,
  payload: Partial<Pick<Ticket, "status" | "order" | "title" | "priority">>,
): Promise<Ticket> {
  return request<Ticket>(`/tickets/${ticketId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
