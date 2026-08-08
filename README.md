# AgentDesk

Local-first project management and coding-agent orchestration for software development.

AgentDesk is a lightweight engineering cockpit for a human supervising autonomous coding work. It owns project state, ticket state, agent runs, Git workspaces, review state, and activity history while leaving final code approval and merging in GitHub.

## What works today

AgentDesk can currently:

- manage projects, tickets, hierarchy, dependencies, priorities, structured acceptance criteria, and lifecycle state;
- bootstrap its own roadmap into AgentDesk;
- show Board and Epics views with filtering, search, completed-work controls, and epic progress;
- register Git remotes and maintain AgentDesk-owned local clones;
- create isolated ticket worktrees and show live Git status;
- adopt work that already exists on a remote branch or pull request;
- execute local agents and OpenAI Codex CLI runs inside ticket worktrees;
- capture structured run logs, results, usage, commands, and downloadable telemetry;
- inspect changed files and diffs before promotion;
- create or update GitHub pull requests from reviewed ticket work;
- require agents to integrate current `origin/main` and resolve conflicts before review;
- detect merged pull requests and finalize tickets;
- remove worktrees and clean local/remote agent branches after merge;
- preserve an append-only ticket activity history for ticket, workspace, Git, and agent events.

AgentDesk is actively dogfooding itself: AgentDesk stories can be implemented by Codex inside AgentDesk-managed workspaces, reviewed in AgentDesk, promoted to GitHub, merged by a human, and finalized back in AgentDesk.

## Product principles

- **AgentDesk owns project state.** Projects, tickets, dependencies, runs, events, workspace metadata, and workflow state live in AgentDesk.
- **Git owns code history.** AgentDesk orchestrates branches and worktrees but does not replace Git.
- **GitHub is the merge authority.** AgentDesk may create and update pull requests; a human still approves and merges them.
- **Agents are replaceable workers.** Agent execution sits behind provider/adapter boundaries rather than being embedded in ticket logic.
- **Structured state beats opaque chat.** Work is represented through tickets, events, artifacts, diffs, and state transitions.
- **Human attention is explicit.** Runs that cannot safely proceed become `Needs Human` rather than guessing indefinitely.
- **Local-first.** V1 is intentionally one user, one machine, SQLite, localhost, and AgentDesk-owned Git storage.

## Current development workflow

A typical coding story now follows this lifecycle:

```text
Backlog / Ready
      ↓
Create or adopt workspace
      ↓
Run Codex
      ↓
Fetch latest origin/main
      ↓
Agent integrates main and resolves conflicts
      ↓
Validation / tests / build
      ↓
Review
      ↓
Create PR or Update PR
      ↓
Human reviews and merges in GitHub
      ↓
Sync & finalize
      ↓
Done + worktree/branch cleanup
```

AgentDesk does not ask Codex to push or merge. Codex works only inside the assigned worktree. AgentDesk owns promotion to the review branch, and GitHub remains the human approval boundary.

If work already exists outside AgentDesk, use **Actions → Adopt existing work** on a ticket. Adoption is branch-first: AgentDesk fetches the existing remote branch, creates an AgentDesk-owned worktree from it, and can discover an associated pull request when one exists.

## Ticket workflow

Primary workflow:

```text
Backlog → Ready → In Progress → Review → Done
```

Additional operational states include:

- `Blocked`
- `Needs Human`
- `Agent Failed`
- `Cancelled`

A waiting ticket becomes actionable only when its dependencies are satisfied. Agent runs automatically move actionable tickets into `In Progress`, then into `Review` only when reviewable work exists and unresolved Git conflicts do not remain.

## Git and workspace model

Projects register Git **remotes**, not arbitrary local folders.

AgentDesk owns a canonical clone for each registered repository under:

```text
~/.agentdesk/repositories/<repository-id>/clone
```

Ticket work happens in isolated worktrees under:

```text
~/.agentdesk/workspaces/<repository-id>/<workspace-id>
```

New ticket workspaces normally use a branch such as:

```text
agent/AD-42
```

AgentDesk can also adopt an existing remote branch instead of creating a new one.

The workspace/review layer tracks:

- clean/dirty Git state;
- staged, modified, and untracked files;
- ahead/behind state when available;
- HEAD commit information;
- changed files and unified diff;
- pull request number, URL, and merge state;
- whether local work has not yet been published to the PR branch.

After a PR is merged, **Sync & finalize** marks the ticket Done, records the merge, removes the AgentDesk worktree, deletes managed local/remote agent branches, and prunes Git metadata. Cleanup is deliberately tolerant of Windows long-path and read-only-file edge cases so disposable workspace residue cannot block ticket finalization.

## Agent execution

The current production dogfood path uses the OpenAI Codex CLI adapter.

AgentDesk invokes Codex non-interactively in the ticket worktree, sends the structured ticket brief over stdin, and captures JSONL telemetry into persistent run logs.

The agent receives instructions to:

- work only in the assigned AgentDesk worktree;
- inspect repository instructions and existing code;
- integrate the fetched default branch into its current branch when needed;
- resolve merge conflicts before continuing;
- implement only the assigned ticket;
- run relevant validation;
- leave the workspace conflict-free;
- never push, create a PR, or merge its branch into another branch.

Successful reruns for an existing pull request can update that PR branch automatically after the agent has resolved conflicts and validation succeeds.

## Activity and review

Ticket detail includes an append-only Activity view. Activity can be filtered by ticket, agent, Git, and workspace events and is paginated so long-running tickets remain readable.

Agent run logs can be downloaded from the UI.

The Review section shows the branch diff against the repository default branch and supports:

- **Request changes**
- **Create PR**
- **Update PR #…**
- **Open PR #… in GitHub**
- **Sync & finalize** after merge

## Running AgentDesk locally

From the repository root:

```powershell
just setup
just bootstrap
just run
```

`just run` opens the API and web development servers in separate Windows terminals. You can also double-click `run.cmd`.

Useful commands:

```powershell
just test
just web-build
just migrate
just migration-check
just bootstrap
```

Default development URLs:

```text
Web: http://localhost:5173
API: http://127.0.0.1:8000
```

## Core domain model

```text
Project
├── Repository
│   └── Workspace
└── Ticket
    ├── hierarchy / dependencies
    ├── structured requirements
    ├── activity events
    ├── agent runs
    └── Git / pull-request review state
```

Tickets support machine-readable planning fields alongside their human-readable description:

```yaml
goal:
acceptance_criteria: []
constraints: []
definition_of_done: []
relevant_files: []
context: []
estimated_complexity:
requires_human: false
```

## Current stack

```text
Frontend:       React + TypeScript + Vite
Backend:        Python + FastAPI
Persistence:    SQLite
ORM/migrations: SQLAlchemy + Alembic
Validation:     Pydantic
Agent runtime:  Python subprocess adapters
Coding agent:   OpenAI Codex CLI
Source control: Git + AgentDesk-owned clones/worktrees
PR authority:   GitHub / gh CLI
Testing:        pytest + frontend build validation
```

## Roadmap status

The original numbered roadmap is now stored as real AgentDesk tickets and should be treated as the authoritative planning surface rather than duplicated as a large checkbox list in this README.

Broadly, the project has completed the foundations for:

- ticket/project persistence and structured planning;
- dependency-aware workflow;
- usable project and ticket UI;
- event/activity history;
- managed Git repositories and worktrees;
- agent/run persistence and local execution;
- Codex provider integration;
- human review and GitHub PR promotion.

Major capabilities still ahead include richer planning/Chief-of-Staff behavior, independent automated reviewer agents, scheduling/parallel dispatch, and a human-attention console.

Use AgentDesk itself to inspect the current roadmap, epic progress, and next executable stories.

## Explicitly out of scope for V1

- Multi-tenant SaaS hosting.
- Enterprise authentication/authorization.
- Jira/Linear compatibility.
- Mobile apps.
- Kubernetes or distributed worker infrastructure.
- Autonomous merging to protected/default branches.
- Large catalogs of specialized agent personas.
- Building our own LLM.

## Definition of success

AgentDesk succeeds when the normal interaction changes from:

> open tickets, assign work, watch agents, read logs, repair orchestration manually

into:

> describe intent, approve the plan, inspect exceptions, approve good work

The system should make autonomous engineering more observable and controllable, not merely more autonomous.
