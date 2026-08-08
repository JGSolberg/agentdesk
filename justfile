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
    uv run uvicorn apps.api.agentdesk_api.main:app --reload