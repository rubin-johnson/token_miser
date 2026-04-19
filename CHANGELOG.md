# Changelog

## [Unreleased]

## [0.2.0] - 2026-04-18

### Added
- Codex backend (`backends/codex.py`) — run benchmarks against Codex CLI alongside Claude
- `--agent` flag: `claude`, `codex`, or `both` for all run/tune commands
- `--order baseline-first|package-first` for crossover experimental design
- `scripts/run-suite-package-matrix.sh` — unified matrix runner across agents and packages
- `token-miser list` — shows available packages from the configured directory
- `--packages-dir` flag and `TOKEN_MISER_PACKAGES_DIR` env var for configurable package location
- `TOKEN_MISER_DB` env var override for database path (useful for CI isolation)
- `backend.estimate_cost(usage, model)` — per-backend cost estimation from token counts
- Claude pricing table in `ClaudeBackend` (haiku/sonnet/opus, cache-aware)
- 7 new packages: `caveman`, `c-structured`, `piersede`, `thinking-cap`, `planner`, `drona23`, `adversarial-frugal`
- 3 domain benchmark suites: `domain-python-api`, `domain-iac`, `domain-frontend` (24 tasks total)
- Axis suite: 8 tasks isolating distinct tool-interaction patterns
- `token-miser matrix` — cross-package comparison grid (text + JSON export)

### Changed
- `loadouts/` directory renamed to `packages/` to align with kanon terminology
- Package names: `slim-rubin` → `lean`, `full-rubin` → `personal`
- `loadout` dependency now resolved from git URL (no local path required)

### Fixed
- `--model` flag now propagates correctly through executor and run command
- `--skip-baseline` now fetches the previous session correctly
- Baseline temp directory no longer leaks on early-exit paths in tune.py

## [0.1.0] - 2026-04-15

Initial Python release. Complete rewrite from Go.

### Added
- `token-miser run` — execute a task under baseline and package configurations
- `token-miser compare` — side-by-side comparison of runs
- `token-miser analyze` — statistical summary (mean, stdev, median per package)
- `token-miser history` — list all recorded runs
- `token-miser show` — inspect a specific run in detail
- `token-miser tasks` — list available task YAML files
- `token-miser migrate` — initialize or migrate the database
- `token-miser tune` — automated package evaluation against benchmark suites
- `token-miser recommend` — generate package configuration recommendations from tune results
- SQLite persistence with automatic schema migration
- Three initial packages: `token-miser`, `thorough`, `tdd-strict`
- Kanon integration for distributing packages across machines
- LLM-as-judge quality scoring for task evaluation
- GitHub Actions CI
- Apache 2.0 license

### Removed
- All Go code
