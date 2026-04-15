# Changelog

## [0.1.0] - 2026-04-15

Complete rewrite from Go to Python.

### Added

- `token-miser run` - execute tasks under control and treatment arms
- `token-miser compare` - side-by-side comparison of runs
- `token-miser analyze` - statistical summary (mean, stdev, median per arm)
- `token-miser history` - list all recorded runs
- `token-miser show` - inspect a specific run in detail
- `token-miser tasks` - list available task YAML files
- `token-miser migrate` - initialize or migrate the database
- Configurable per-invocation timeout (`--timeout`, default 600s)
- Environment variable expansion in task YAML (`${EXPERIMENT_REPO}`)
- Quality scoring warnings to stderr (no longer silently swallowed)
- Three loadout bundles: token-miser, thorough, tdd-strict
- Kanon integration: `.kanon` config and docs/kanon-integration.md
- GitHub Actions CI
- Apache 2.0 license

### Removed

- All Go code
- Old Python budget-tracking code (replaced with A/B testing framework)
