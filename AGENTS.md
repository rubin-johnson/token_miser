# token_miser

## Purpose
- `token_miser` benchmarks coding-agent configurations and records token usage, cost, and task outcomes.
- Preserve compatibility for both Claude and Codex backends when changing execution, reporting, or schema code.

## Common Commands
- Install/sync: `uv sync`
- Tests: `uv run pytest -q`
- Lint: `uv run ruff check src tests`
- CLI help: `uv run token-miser --help`

## Repo Notes
- Main CLI entrypoint: `src/token_miser/__main__.py`
- Execution backends live under `src/token_miser/backends/`
- Benchmark environment setup lives in `src/token_miser/environment.py`
- Persisted run data schema lives in `src/token_miser/db.py`
- Loadout packages used for experiments live in `packages/`

## Working Rules
- Keep backend additions additive; do not regress existing Claude behavior while adding Codex support.
- Prefer updating tests with code changes, especially for CLI, DB, and report output.
- If a schema change is required, add migration logic in `init_db()` rather than forcing a fresh database.
