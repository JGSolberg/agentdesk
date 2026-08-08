export type SearchResult = {
  kind: "ticket" | "project" | "repository" | string;
  id: string;
  label: string;
  subtitle: string;
  href: string;
  archived: boolean;
};

const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export async function globalSearch(query: string): Promise<SearchResult[]> {
  const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&limit=20`);
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
  return response.json() as Promise<SearchResult[]>;
}
