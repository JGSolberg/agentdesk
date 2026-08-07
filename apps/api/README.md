# AgentDesk API

## Run locally

From `apps/api`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
uvicorn agentdesk_api.main:app --reload
```

The API starts at `http://127.0.0.1:8000` and OpenAPI docs are available at `/docs`.
By default, local data is stored in `.agentdesk/agentdesk.db` relative to the working directory.

## Tests

```bash
pytest
```
