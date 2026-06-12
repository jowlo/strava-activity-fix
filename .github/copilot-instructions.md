# Copilot Instructions

## Build & Run

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and Python 3.12+.

```bash
# Install dependencies
uv sync

# Run locally (one-shot)
uv run strava-activity-hide --config ./config/config.yaml --once

# Run OAuth flow
uv run strava-activity-hide --config ./config/config.yaml --auth

# Dry-run override (no changes applied)
uv run strava-activity-hide --config ./config/config.yaml --once --dry-run

# Docker
docker compose up -d
```

There are no tests or linters configured in this project.

## Architecture

The app is a scheduled service that periodically fetches Strava activities and applies user-defined rules to them.

**Core flow** (`app/main.py`):
1. Load YAML config → authenticate with Strava OAuth2 → enter scheduler loop
2. Each tick: fetch activities newer than last checkpoint → evaluate each activity against all rules → apply matching actions
3. Persist `last_check` timestamp to `state.json` so activities aren't reprocessed

**Key modules:**
- `strava_client.py` — Strava API wrapper with automatic token refresh. All API calls go through `_request()` which handles auth headers and token renewal.
- `rules.py` — Rule engine: condition evaluation (with dot-notation field access), operator dispatch, and action execution (hide/mute/delete/update).
- `config.py` — YAML loading + validation. Paths for tokens/state are resolved relative to the config file or via env vars.
- `auth_server.py` — Ephemeral HTTP server on port 8000 to capture the OAuth callback code.
- `generator.py` — Generates a starter `config.yaml` from a Python dict template.

**State files** (stored alongside config, typically in `./config/`):
- `config.yaml` — User rules and Strava credentials
- `tokens.json` — OAuth access/refresh tokens (auto-refreshed)
- `state.json` — Scheduler state (`last_check` timestamp)

## Conventions

- Entry point is `app/main.py:main`, registered as the `strava-activity-hide` script in `pyproject.toml`.
- No class hierarchy for rules — everything is plain dicts processed by functions. Rules, conditions, and actions are all dict-based, defined in YAML.
- Dot notation resolves nested activity fields (e.g., `map.summary_polyline`) via `_resolve_field()`.
- Actions can be specified as strings (`"hide"`) or dicts (`{"type": "update", "fields": {...}}`). Both forms are normalized in `get_actions()`.
- The `dry_run` flag is threaded through to `apply_actions()` — when true, actions are logged but not executed.
- Environment variables `CONFIG_PATH`, `TOKENS_PATH`, `STATE_PATH` override default paths (used in Docker).
