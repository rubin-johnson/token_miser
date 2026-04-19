# token_miser

Benchmarks coding-agent configurations; records token usage, cost, and task outcomes.

## Common Commands
- Install/sync: `uv sync`
- Tests: `uv run pytest -q`
- Lint: `uv run ruff check src tests`
- Format: `uv run ruff format src tests`
- CLI help: `uv run token-miser --help`

## Repo Notes
- Main CLI entrypoint: `src/token_miser/__main__.py`
- Execution backends: `src/token_miser/backends/` (claude, codex) — extend `base.py`
- Benchmark environment setup: `src/token_miser/environment.py`
- Run data schema: `src/token_miser/db.py`
- Loadout integration: `src/token_miser/package_adapter.py` — wraps loadout's `apply_package`
- Package publishing to kanon: `src/token_miser/publish.py`
- Experiment packages live in `packages/`

## Working Rules
- Keep backend additions additive; do not regress existing Claude behavior while adding Codex support
- Depends on loadout (editable install via uv sources) — `uv sync` resolves it, bare `pip install` does not
- Schema changes need migration logic in `init_db()`, not fresh database creation
- `checker.py` evaluates success criteria — changes affect all benchmark results, test carefully
- `package_adapter.py` guards against PyPI's unrelated `loadout` package — don't remove that import check
