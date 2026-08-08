set shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# AgentDesk

default:
    @just --list

setup:
    uv sync

test:
    uv run pytest

lint:
    uv run ruff check .

format:
    uv run ruff format .

api:
    uv run uvicorn agentdesk_api.main:app --reload

# Create a new database migration
migration message:
    uv run alembic -c apps/api/alembic.ini revision --autogenerate -m "{{message}}"

# Upgrade database to latest schema
migrate:
    uv run alembic -c apps/api/alembic.ini upgrade head

# Show current database migration revision
migration-status:
    uv run alembic -c apps/api/alembic.ini current

# Verify database is at all migration heads
migration-check:
    uv run alembic -c apps/api/alembic.ini current --check-heads