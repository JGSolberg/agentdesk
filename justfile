set shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# AgentDesk

default:
    @just --list

# Install Python and web dependencies
setup:
    uv sync
    pnpm --dir apps/web install

# Run all Python tests
test:
    uv run pytest

# Run Ruff
lint:
    uv run ruff check .

# Format Python
format:
    uv run ruff format .

# Start FastAPI
api:
    uv run uvicorn agentdesk_api.main:app --reload

# Start the Vite web app
web:
    pnpm --dir apps/web dev

# Start API and web in separate PowerShell windows
dev:
    $root = (Get-Location).Path; Start-Process powershell.exe -ArgumentList '-NoExit','-NoLogo','-Command',("$Host.UI.RawUI.WindowTitle = ''AgentDesk API''; Set-Location -LiteralPath ''{0}''; just api" -f $root); Start-Process powershell.exe -ArgumentList '-NoExit','-NoLogo','-Command',("$Host.UI.RawUI.WindowTitle = ''AgentDesk Web''; Set-Location -LiteralPath ''{0}''; just web" -f $root)

# Build the web app
web-build:
    pnpm --dir apps/web build

# Create a new database migration
migration message:
    uv run alembic -c apps/api/alembic.ini revision --autogenerate -m "{{message}}"

# Upgrade database to latest schema
migrate:
    uv run alembic -c apps/api/alembic.ini upgrade head

# Create/update the local AgentDesk project and roadmap
bootstrap: migrate
    uv run python -m agentdesk_api.bootstrap
    uv run python -m agentdesk_api.roadmap_identity
    uv run python -m agentdesk_api.roadmap_epics

# Show current database migration revision
migration-status:
    uv run alembic -c apps/api/alembic.ini current

# Verify database is at all migration heads
migration-check:
    uv run alembic -c apps/api/alembic.ini current --check-heads
