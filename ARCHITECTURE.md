# AgentDesk Architecture

AgentDesk is a local-first monorepo with a FastAPI backend, React/Vite frontend, SQLite persistence, and AgentDesk-owned Git clones/worktrees.

There is intentionally no top-level `src/` directory.

## Repository layout

```text
agentdesk/
├── apps/
│   ├── api/
│   │   ├── agentdesk_api/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   └── main.py
│   │   ├── alembic/
│   │   └── tests/
│   └── web/
│       ├── src/
│       └── public/
├── run.cmd
├── justfile
├── README.md
├── ARCHITECTURE.md
└── .gitignore
```

The React app uses its conventional `apps/web/src/` directory. Backend routing, persistence models, schemas, repositories, and services live under `apps/api/agentdesk_api/`.

## Runtime boundaries

```text
Browser / React
      ↓ HTTP
FastAPI
      ├── ticket/project services
      ├── event ledger
      ├── repository/workspace services
      ├── review / PR services
      └── agent runtime
              ↓ subprocess adapter
           Codex CLI
```

SQLite is the local system of record for AgentDesk state. Git is the source of truth for code history. GitHub is the approval/merge authority for pull requests.

## Git ownership model

AgentDesk repositories represent remotes. AgentDesk owns the local clone and worktrees used for execution.

```text
~/.agentdesk/
├── repositories/
│   └── <repository-id>/
│       └── clone/
└── workspaces/
    └── <repository-id>/
        └── <workspace-id>/
```

The canonical clone is not the user's development checkout. Ticket execution occurs in isolated worktrees so simultaneous stories do not share a mutable working directory.

A new ticket workspace normally creates an `agent/<ticket-key>` branch from the repository default branch. Existing work can instead be adopted from a remote branch or pull request.

Workspace cleanup is explicit and idempotent. After a merged PR is finalized, AgentDesk removes the worktree, deletes managed agent branches, prunes Git metadata, and records lifecycle events. Windows long-path/read-only cleanup failures are treated as disposable filesystem residue rather than reasons to leave a merged ticket unfinished.

## Ticket and execution model

A Ticket contains human-readable planning text plus structured fields such as acceptance criteria, constraints, definition of done, relevant files, complexity, and dependencies.

An AgentRun snapshots the ticket context used for execution. This keeps an individual run explainable even if the ticket is edited later.

Current execution flow:

```text
Ticket + active workspace
        ↓
AgentRun created
        ↓
fetch origin/default-branch
        ↓
Codex CLI executes in worktree
        ↓
Codex integrates default branch when required
        ↓
implementation + validation
        ↓
conflict check
        ↓
Review or Needs Human / Agent Failed
```

Codex is deliberately not responsible for promotion. It may integrate the fetched default branch into its current AgentDesk branch, but it must not push, open PRs, or merge its branch elsewhere.

## Review and GitHub promotion

The review layer compares the ticket branch against the current repository default branch and exposes changed files, diff statistics, unified diff, PR metadata, and unpublished local state.

```text
Review
  ↓
Create PR / Update PR
  ↓
GitHub human review + merge
  ↓
Sync & finalize
  ↓
Done + cleanup
```

If an existing PR becomes stale because an agent resolved conflicts locally, AgentDesk compares local HEAD with the PR head SHA and updates the same PR branch instead of creating a duplicate.

After GitHub reports the PR merged, Update PR is no longer a valid action; the ticket moves into finalization.

## Event ledger

Ticket history is append-only. Events capture ticket lifecycle changes, dependency changes, workspace creation/reactivation/removal/adoption, agent run transitions, and Git/PR workflow events.

The frontend presents Activity as a filtered, paginated timeline rather than requiring users to inspect raw logs for normal workflow understanding.

Agent logs remain separately available and downloadable for execution-level diagnostics.

## Provider boundary

Agent execution is adapter-based. The current working coding provider is OpenAI Codex CLI, invoked through a subprocess adapter with structured stdin context and JSONL output parsing.

Provider-specific execution concerns remain outside ticket and project persistence logic so other coding backends can be added later without redefining AgentDesk's workflow model.

## Local development

`just run` is the primary development launcher. On Windows it delegates to `run.cmd`, which opens API and web development servers in separate terminals.

Common validation commands:

```powershell
just test
just web-build
just migrate
just migration-check
just bootstrap
```

The architecture intentionally favors simple local components and explicit lifecycle boundaries over distributed infrastructure. Complexity should be added only when the local-first orchestration model has earned it.
