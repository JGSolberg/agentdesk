# AgentDesk Architecture

AgentDesk uses a monorepo layout with executable applications under `apps/` and reusable shared code under `packages/`.

There is intentionally no top-level `src/` directory.

```text
agentdesk/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── web/
│       ├── src/
│       ├── public/
│       └── package.json
├── packages/
│   ├── core/
│   ├── orchestration/
│   ├── providers/
│   ├── git/
│   └── prompts/
├── scripts/
├── README.md
└── .gitignore
```

The React app may use its conventional internal `src/` directory. The backend uses an `app/` Python package. Shared capabilities live under `packages/`.
