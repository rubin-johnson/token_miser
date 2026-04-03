# Observability — notes for ralphael

## Problem
Users can't inspect experiment results without asking Claude to read logs. The CLI needs
to surface all run data directly.

## What's missing

### 1. Data not being stored
- `result` (Claude's full text output) is not persisted to DB
- `wall_seconds` is always 0 in DB (ExecutorResult.WallSeconds not written to db.Run)
- Per-criterion pass/fail detail is lost (only pass count stored, not which ones passed)

### 2. Commands needed
- `show <run-id>` — full detail for one run: arm, task, tokens, cost, wall time,
  criteria results (pass/fail per criterion with detail string), quality scores,
  Claude's output
- `compare --task <id>` should show per-criterion breakdown, not just N/M count

## Schema changes
Add to `runs` table:
- `result TEXT` — Claude's full output
- `wall_seconds REAL` — actually populated (already in ExecutorResult, just not written)

Add new table `criterion_results`:
- `id INTEGER PRIMARY KEY`
- `run_id INTEGER REFERENCES runs(id)`
- `criterion_type TEXT`
- `passed INTEGER` (0/1)
- `detail TEXT`

## CLI changes

### `show <run-id>`
```
token-miser show 3

Run #3 — synth-001 / treatment
  Started:     2026-03-31 11:09:40
  Wall time:   47.3s
  Input:       8,241 tokens
  Output:      2,116 tokens
  Cost:        $0.046
  Criteria:    4/5 passed
    ✓ file_exists pyproject.toml
    ✓ file_exists src/loadout/__init__.py
    ✓ file_exists tests/test_loadout.py
    ✗ file_exists uv.lock  (missing paths: uv.lock)
    ✓ command_exits_zero uv run python -c 'import loadout'
  Quality:
    toolchain:   85
    structure:   90
    tdd_readiness: 75
    code_quality: 88
  Output:
    [Claude's actual response text]
```

### `compare --task <id>` improvements
Show per-criterion pass rate across arms (% passed across all runs for that arm/task).

## AC
- `show` command prints full run detail as above
- `wall_seconds` is non-zero in history output
- `criterion_results` table populated on every run
- `compare` shows per-criterion breakdown
- All new commands have tests
