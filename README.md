# AgentDesk

Local-first project management and agent orchestration for software development.

AgentDesk owns project state; model providers and coding agents are replaceable execution backends. The goal is not to recreate Jira. The goal is to build a lightweight engineering cockpit designed for a human supervising autonomous software agents.

## Product principles

- **AgentDesk owns the truth.** Projects, tickets, dependencies, agent runs, events, and approvals live in AgentDesk rather than in an external issue tracker.
- **Agents are replaceable workers.** GitHub Copilot, OpenAI, Anthropic, local models, or future providers plug in behind common interfaces.
- **Git remains the code source of truth.** Every coding task operates in an isolated branch/worktree and produces inspectable commits and diffs.
- **Structured state beats agent chat.** Agents communicate through tickets, events, artifacts, and explicit state transitions rather than opaque conversations.
- **Human approval is first-class.** The system makes it obvious when work needs a person rather than letting an agent guess indefinitely.
- **Local-first for V1.** One user, one machine, SQLite, localhost. We earn complexity only when we need it.

## V1 target workflow

1. A user creates or selects a project and associates a Git repository.
2. The user tells the Chief of Staff what they want built.
3. The Chief proposes an Epic with dependency-aware Stories and acceptance criteria.
4. The user approves the execution plan.
5. Ready Stories are dispatched to developer agents in isolated Git worktrees.
6. Agents record structured progress events while they work.
7. A reviewer agent validates acceptance criteria, tests, and the resulting diff.
8. Work that passes review enters a human approval state.
9. The user inspects the ticket, activity, commits, and diff before accepting it.
10. Completing a Story automatically unblocks dependent work.

## Core domain model

```text
Workspace
└── Project
    ├── Repository
    └── Ticket
        ├── Epic
        │   └── Story
        │       └── Task
        ├── Bug
        └── Spike
```

Tickets support machine-readable fields in addition to human-readable descriptions:

```yaml
goal:
acceptance_criteria: []
constraints: []
definition_of_done: []
relevant_files: []
dependencies: []
context: []
estimated_complexity:
requires_human: false
```

## Ticket workflow

```text
Backlog -> Ready -> In Progress -> Review -> Done
```

Additional operational states: `Blocked`, `Needs Human`, `Agent Failed`.

A ticket should only enter `Ready` when its dependencies are satisfied.

---

# Build plan

This README is the project checklist. Check items off only when the implementation exists in the repository and its acceptance criteria are met.

## Milestone 0 — Repository foundation

- [x] Create `JGSolberg/agentdesk` repository.
- [x] Establish AgentDesk product direction and build plan.
- [ ] Add repository structure for `apps/api`, `apps/web`, and shared packages.
- [ ] Add root `.gitignore` and development environment documentation.
- [ ] Add one-command local startup for API and web app.
- [ ] Add basic automated test commands for backend and frontend.
- [ ] Add Alembic migrations so existing local databases evolve safely as models change.
- [ ] Add migration tests for upgrading an existing SQLite database.

**Milestone complete when:** a fresh clone can be installed, tested, started locally, and upgraded between schema versions from documented commands.

## Milestone 1 — Ticket core

### AD-1: Project persistence

- [x] Create `Project` database model.
- [x] Support create, read, update, and list operations.
- [x] Give every project a stable ID, name, optional description, timestamps, and archived flag.
- [x] Add API tests.

### AD-2: Ticket persistence

- [x] Create `Ticket` database model.
- [x] Support ticket types: Epic, Story, Task, Bug, Spike.
- [x] Support parent-child hierarchy.
- [x] Support ticket statuses: Backlog, Ready, In Progress, Review, Done, Blocked, Needs Human, Agent Failed.
- [x] Support title, description, priority, timestamps, and ordering.
- [x] Generate human-friendly project ticket keys such as `AD-42`.
- [x] Add API tests.

### AD-3: Structured ticket fields

- [x] Add goal.
- [x] Add acceptance criteria.
- [x] Add constraints.
- [x] Add definition of done.
- [x] Add relevant files/context.
- [x] Add estimated complexity.
- [x] Add `requires_human`.
- [x] Expose fields through the API.

### AD-4: Dependencies

- [ ] Add ticket-to-ticket dependency relationships.
- [ ] Prevent obvious circular dependencies.
- [ ] Expose blocked/unblocked state through the API.
- [ ] Automatically identify tickets whose dependencies are complete.
- [ ] Add dependency tests.

**Milestone complete when:** AgentDesk can reliably represent a real software backlog without any AI functionality.

## Milestone 2 — Usable project UI

### AD-5: Application shell

- [ ] Create React/Vite frontend.
- [ ] Add project selector/sidebar.
- [ ] Add project overview route.
- [ ] Establish a clean dark-mode-first visual system.

### AD-6: Kanban board

- [ ] Display ticket columns by status.
- [ ] Display ticket key, title, type, priority, and assignee/agent when present.
- [ ] Create tickets from the UI.
- [ ] Drag/drop tickets between valid states.
- [ ] Persist status/order changes through the API.
- [ ] Make Blocked, Needs Human, and Agent Failed visually obvious.

### AD-7: Ticket detail view

- [ ] Display and edit human-readable description.
- [ ] Display and edit structured agent fields.
- [ ] Display parent/children.
- [ ] Display dependencies and dependents.
- [ ] Display activity timeline placeholder.
- [ ] Support manual status transition.

**Milestone complete when:** the human ticket-management experience is useful enough that we would choose it over a lightweight Trello board for a personal software project.

## Milestone 3 — Event ledger

### AD-8: Event model

- [ ] Create append-only event storage.
- [ ] Record event type, timestamp, actor, project, ticket, run, and structured payload.
- [ ] Define initial event vocabulary: `ticket.created`, `ticket.updated`, `ticket.status_changed`, `agent.started`, `agent.progress`, `agent.completed`, `agent.failed`, `review.completed`, `human.approved`, `human.rejected`.
- [ ] Add query API for project/ticket event timelines.

### AD-9: Activity UI

- [ ] Render ticket activity timeline.
- [ ] Distinguish human, system, and agent actors.
- [ ] Show concise structured summaries instead of raw JSON by default.
- [ ] Allow inspection of raw event payloads.

**Milestone complete when:** we can explain exactly what happened to any ticket without reading agent logs.

## Milestone 4 — Git workspace management

### AD-10: Repository registration

- [ ] Associate one or more local Git repositories with a project.
- [ ] Validate repository paths.
- [ ] Record default branch and repository metadata.
- [ ] Display repository health/status in the UI.

### AD-11: Worktree manager

- [ ] Create one isolated Git worktree per active coding ticket.
- [ ] Use deterministic branch names such as `agent/AD-42-short-title`.
- [ ] Detect existing/conflicting worktrees safely.
- [ ] Clean up completed/abandoned worktrees explicitly.
- [ ] Never destroy uncommitted work automatically.
- [ ] Add integration tests around Git operations.

### AD-12: Git artifacts

- [ ] Record branch and worktree on the ticket/run.
- [ ] Record commits produced by an agent.
- [ ] Show changed files and diff summary in the ticket UI.
- [ ] Provide a path to inspect the full diff.

**Milestone complete when:** multiple tickets can be worked simultaneously without sharing a mutable working tree.

## Milestone 5 — Agent runtime foundation

### AD-13: Provider interface

- [ ] Define provider-neutral `AgentModel` / session interface.
- [ ] Define tool invocation interface.
- [ ] Define standardized responses, errors, token/usage metadata where available.
- [ ] Keep ticketing and orchestration code free of provider-specific imports.

### AD-14: GitHub Copilot adapter

- [ ] Implement the first provider adapter using the supported GitHub Copilot agent/SDK path.
- [ ] Support session creation.
- [ ] Support custom tools.
- [ ] Stream or capture progress into AgentDesk events.
- [ ] Handle provider failure cleanly.

### AD-15: Agent run model

- [ ] Persist every agent invocation as an `AgentRun`.
- [ ] Track role, provider, model, ticket, start/end time, status, and result.
- [ ] Track failure reason and retries.
- [ ] Expose run history in the UI.

**Milestone complete when:** AgentDesk can execute a simple provider-backed agent and fully account for the run in structured state.

## Milestone 6 — Chief of Staff

### AD-16: Planning agent

- [ ] Add Chief of Staff role.
- [ ] Accept a natural-language project request.
- [ ] Read relevant project/ticket state.
- [ ] Propose an Epic and Stories.
- [ ] Produce acceptance criteria and definitions of done.
- [ ] Produce explicit dependencies between Stories.
- [ ] Estimate rough complexity.
- [ ] Do not start coding automatically.

### AD-17: Plan approval UI

- [ ] Present proposed execution plan before persistence/execution.
- [ ] Allow editing proposed tickets.
- [ ] Allow approve/reject/regenerate.
- [ ] Persist approved plan as normal AgentDesk tickets.

### AD-18: Agent Brief generator

- [ ] Generate a bounded work packet for a Story.
- [ ] Include why the work exists.
- [ ] Include goal and acceptance criteria.
- [ ] Include relevant architecture/context.
- [ ] Include explicit `do not change` constraints.
- [ ] Include dependencies and definition of done.

**Milestone complete when:** a user can describe a feature and receive a credible, editable, dependency-aware implementation backlog.

## Milestone 7 — Developer agent

### AD-19: Developer tools

- [ ] Provide bounded file read/search tools.
- [ ] Provide bounded file edit/create tools.
- [ ] Provide test/lint command execution.
- [ ] Provide Git status/diff tools.
- [ ] Provide explicit commit tool.
- [ ] Restrict tools to the assigned worktree.

### AD-20: Developer execution loop

- [ ] Claim a Ready Story.
- [ ] Generate/read Agent Brief.
- [ ] Create worktree.
- [ ] Execute coding session.
- [ ] Record progress events.
- [ ] Run required validation.
- [ ] Commit completed work.
- [ ] Transition ticket to Review.
- [ ] Transition to Agent Failed or Needs Human when appropriate.

**Milestone complete when:** a developer agent can implement a tightly scoped Story without modifying another ticket's workspace.

## Milestone 8 — Reviewer agent

### AD-21: Automated review

- [ ] Read Story requirements and definition of done.
- [ ] Inspect diff and commits.
- [ ] Run or verify tests/lint.
- [ ] Check acceptance criteria individually.
- [ ] Flag unrelated refactors.
- [ ] Produce structured pass/fail findings.

### AD-22: Review workflow

- [ ] Passing review moves work to Needs Human approval.
- [ ] Failed review returns actionable findings to the Story.
- [ ] Developer agent can receive a bounded repair run.
- [ ] Limit automatic review/fix loops to prevent infinite churn.

**Milestone complete when:** no agent-authored code reaches human approval without an independent structured review.

## Milestone 9 — Scheduler and parallel work

### AD-23: Dependency scheduler

- [ ] Detect Stories eligible to move from Backlog/Blocked to Ready.
- [ ] Dispatch only when dependencies are satisfied.
- [ ] Respect configurable concurrency limits.
- [ ] Prevent duplicate dispatch of the same ticket.

### AD-24: Parallel execution

- [ ] Run multiple developer agents concurrently in separate worktrees.
- [ ] Display active/waiting/blocked workers in the UI.
- [ ] Surface branch conflicts rather than guessing through them.

### AD-25: Epic progress

- [ ] Roll Story status into Epic completion percentage.
- [ ] Show critical blockers.
- [ ] Show currently executable next work.

**Milestone complete when:** approving an Epic can safely drive multiple independent Stories through execution according to their dependency graph.

## Milestone 10 — Chief of Staff console

### AD-26: Conversational project control

- [ ] Add persistent Chief of Staff panel.
- [ ] Answer questions from structured AgentDesk state.
- [ ] Summarize progress, failures, blockers, and decisions needed.
- [ ] Support commands such as "pause this epic", "what is blocked?", and "plan the next feature".
- [ ] Require explicit approval for destructive or high-impact actions.

### AD-27: Human attention queue

- [ ] Aggregate Needs Human tickets.
- [ ] Aggregate failed runs needing intervention.
- [ ] Aggregate pending plan approvals.
- [ ] Aggregate code awaiting human approval.
- [ ] Make this the primary inbox for the human operator.

**V1 complete when:** one person can describe a feature, approve a plan, supervise parallel autonomous implementation, inspect the resulting code/review evidence, and primarily intervene only where AgentDesk explicitly asks for human judgment.

---

# Technical direction

```text
Frontend:       React + TypeScript + Vite
Backend:        Python + FastAPI
Persistence:    SQLite
ORM/migrations: SQLAlchemy + Alembic
Validation:     Pydantic
Agent runtime:  Python
First provider: GitHub Copilot adapter
Source control: Git + worktrees
Testing:        pytest + frontend test tooling
```

Repository layout:

```text
agentdesk/
├── apps/
│   ├── api/
│   │   ├── agentdesk_api/
│   │   └── tests/
│   └── web/
│       ├── src/
│       └── public/
├── packages/
│   ├── core/
│   ├── orchestration/
│   ├── providers/
│   ├── git/
│   └── prompts/
├── scripts/
├── ARCHITECTURE.md
├── README.md
└── .gitignore
```

There is intentionally **no top-level `src/`**. Executable applications live under `apps/`; reusable capabilities live under `packages/`. A frontend app may have its conventional `apps/web/src/` directory.

## Explicitly out of scope for V1

- Multi-tenant SaaS hosting.
- Enterprise authentication/authorization.
- Jira/Linear compatibility.
- Mobile apps.
- Kubernetes.
- Distributed worker infrastructure.
- Autonomous merging to protected/default branches.
- Large catalogs of specialized agent personas.
- Building our own LLM.

## Definition of success

AgentDesk succeeds when the normal interaction changes from:

> open tickets, assign work, watch agents, read logs, repair orchestration manually

into:

> describe intent, approve the plan, inspect exceptions, approve good work

The system should make autonomous engineering more observable and controllable, not merely more autonomous.
