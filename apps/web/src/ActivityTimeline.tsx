import { useMemo, useState } from "react";

import type { TicketEvent } from "./api/tickets";

const PAGE_SIZE = 10;
type ActivityFilter = "all" | "ticket" | "agent" | "git" | "workspace";

function category(event: TicketEvent): ActivityFilter {
  if (event.event_type.startsWith("agent_run_")) return "agent";
  if (event.event_type.startsWith("workspace_")) return "workspace";
  if (event.event_type.startsWith("pull_request_") || event.event_type.startsWith("git_")) return "git";
  return "ticket";
}

function summary(event: TicketEvent): string {
  if (event.event_type === "ticket_created") return "Ticket created";
  if (event.event_type === "ticket_cancelled") return "Ticket cancelled";
  if (event.event_type === "ticket_reopened") return "Ticket reopened";
  if (event.event_type === "ticket_archived") return "Ticket archived";
  if (event.event_type === "ticket_unarchived") return "Ticket unarchived";
  if (event.event_type === "dependency_added") return `Dependency added: ${String(event.payload.dependency_key ?? "ticket")}`;
  if (event.event_type === "dependency_removed") return `Dependency removed: ${String(event.payload.dependency_key ?? "ticket")}`;
  if (event.event_type === "workspace_created") return `Workspace created: ${String(event.payload.branch ?? event.payload.name ?? "workspace")}`;
  if (event.event_type === "workspace_reactivated") return `Workspace reactivated: ${String(event.payload.branch ?? event.payload.name ?? "workspace")}`;
  if (event.event_type === "workspace_removed") return `Workspace removed: ${String(event.payload.branch ?? event.payload.name ?? "workspace")}`;
  if (event.event_type === "agent_run_created") return `Agent run created: ${String(event.payload.agent_name ?? "agent")}`;
  if (event.event_type === "agent_run_updated") return `Agent run: ${String(event.payload.status ?? "updated")}`;
  if (event.event_type === "pull_request_created") return `Pull request created${event.payload.number ? `: #${String(event.payload.number)}` : ""}`;
  if (event.event_type === "pull_request_merged") return `Pull request merged${event.payload.number ? `: #${String(event.payload.number)}` : ""}`;
  if (event.event_type === "ticket_updated") {
    const changes = event.payload.changes as Record<string, { from?: unknown; to?: unknown }> | undefined;
    if (!changes) return "Ticket updated";
    const entries = Object.entries(changes);
    if (entries.length === 1) {
      const [field, change] = entries[0];
      return `${field.replaceAll("_", " ")}: ${String(change.from ?? "—")} → ${String(change.to ?? "—")}`;
    }
    return `Updated ${entries.map(([field]) => field.replaceAll("_", " ")).join(", ")}`;
  }
  return event.event_type.replaceAll("_", " ");
}

export default function ActivityTimeline({ events }: { events: TicketEvent[] }) {
  const [filter, setFilter] = useState<ActivityFilter>("all");
  const [page, setPage] = useState(0);
  const filtered = useMemo(() => [...events].reverse().filter((event) => filter === "all" || category(event) === filter), [events, filter]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function chooseFilter(next: ActivityFilter) { setFilter(next); setPage(0); }

  return <section className="detail-section detail-activity">
    <div className="activity-heading"><div><h2>Activity</h2><p>{filtered.length} event{filtered.length === 1 ? "" : "s"}</p></div><div className="activity-filters">{(["all", "ticket", "agent", "git", "workspace"] as ActivityFilter[]).map((value) => <button type="button" className={filter === value ? "active" : ""} key={value} onClick={() => chooseFilter(value)}>{value}</button>)}</div></div>
    {filtered.length === 0 && <p className="detail-empty">No activity matches this filter.</p>}
    <div className="activity-timeline">{visible.map((event) => <article className="activity-event" key={event.id}><span className="activity-dot" /><div><strong>{summary(event)}</strong><p>{event.actor} · {new Date(event.created_at).toLocaleString()}</p></div></article>)}</div>
    {pageCount > 1 && <div className="activity-pagination"><button type="button" disabled={safePage === 0} onClick={() => setPage(Math.max(0, safePage - 1))}>← Previous</button><span>Page {safePage + 1} of {pageCount}</span><button type="button" disabled={safePage >= pageCount - 1} onClick={() => setPage(Math.min(pageCount - 1, safePage + 1))}>Next →</button></div>}
  </section>;
}
