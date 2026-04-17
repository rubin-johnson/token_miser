# token-miser

A/B test Claude Code configurations.

token-miser runs identical tasks under different Claude Code packages (configuration packages) and measures token usage, cost, and quality. Compare a vanilla Claude Code setup against one with a custom CLAUDE.md, hooks, and tooling to see whether a configuration change is actually worth the overhead.

## Concepts

- **Task** -- A YAML file describing work for Claude to do: a prompt, a target repo, success criteria, and a quality rubric.
- **Package** -- A Claude Code configuration package (a [loadout](https://github.com/rubin-johnson/loadout)) used to execute the task.
- **Run** -- A single execution of a task under one package.
- **Experiment** -- A pair of runs (baseline + package) on the same task.

## Requirements

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated (`claude auth status`)
- [loadout](https://github.com/rubin-johnson/loadout) installed (`uv tool install loadout`)

## Install

```bash
uv tool install .
```

Or run directly:

```bash
uv run token-miser --help
```

## Quick start

```bash
# Set the target repo for tasks
export EXPERIMENT_REPO=$HOME/code/personal/loadout

# Initialize the database
token-miser migrate

# Run an experiment: vanilla (no config) vs. a loadout package
token-miser run \
  --task tasks/synth-001.yaml \
  --baseline vanilla \
  --package token-miser

# Compare the results
token-miser compare --task synth-001

# Statistical analysis
token-miser analyze --task synth-001
```

## Commands

| Command | Purpose |
|---------|---------|
| `run` | Execute a task under baseline and/or package |
| `compare` | Side-by-side comparison of runs for a task |
| `analyze` | Statistical summary (mean, stdev, median per package) |
| `history` | List all recorded runs |
| `show <id>` | Inspect a specific run in detail |
| `list` | List available packages from the packages directory |
| `tasks` | List available task YAML files |
| `migrate` | Initialize or migrate the database |

### run

```bash
token-miser run \
  --task tasks/synth-001.yaml \
  --baseline vanilla \
  --package token-miser \
  --model sonnet \
  --timeout 600
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--task` | (required) | Path to task YAML |
| `--baseline` | (required) | Baseline: `vanilla`, package name, or path |
| `--package` | (optional) | Package to test: name or path |
| `--model` | `sonnet` | Model identifier for metadata |
| `--timeout` | `600` | Per-invocation timeout in seconds |

### Global flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--packages-dir` | `$TOKEN_MISER_PACKAGES_DIR` or `./packages` | Directory containing packages |

Package names (no `/`) resolve to `{packages-dir}/{name}/`. Paths with `/` are used as-is.

## Task format

```yaml
id: my-task
name: "Human-readable name"
repo: "${EXPERIMENT_REPO}"        # resolved from environment
starting_commit: "abc1234"
prompt: |
  What you want Claude to do...
success_criteria:
  - type: file_exists
    paths: ["some/file.py"]
  - type: command_exits_zero
    command: "uv run pytest"
quality_rubric:
  - dimension: "correctness"
    prompt: "Score 0-1 based on..."
```

Task `repo` fields support `${VAR}` expansion from environment variables, so tasks are portable across machines.

## How it works

For each package in an experiment:

1. Create an isolated temp directory as `HOME`
2. Clone the task's target repo and checkout the starting commit
3. Copy Claude credentials into the isolated HOME
4. If package under test: run `loadout apply` to deploy the configuration package
5. Invoke `claude --print --dangerously-skip-permissions --output-format json`
6. Check success criteria against the workspace
7. Optionally score quality via Claude-as-judge (requires `ANTHROPIC_API_KEY`)
8. Store results in SQLite (`~/.token_miser/results.db`)

## Packages

Packages ship in `packages/` and can be referenced by name:

| Package | Philosophy |
|---------|-----------|
| `token-miser` | Minimize tokens -- terse output, lazy reads, no extras |
| `thorough` | Maximize correctness -- read everything, explain reasoning |
| `tdd-strict` | Strict TDD -- failing test first, always |

Each is a valid loadout package with a `manifest.yaml` and `CLAUDE.md`.

To use packages from another directory (e.g. your dotfiles):

```bash
export TOKEN_MISER_PACKAGES_DIR=~/.claude/packages
token-miser list           # show available packages
token-miser tune --package slim-rubin   # resolve by name
```

## Data

All results stored locally in `~/.token_miser/results.db` (SQLite). Nothing is sent externally beyond the Claude API calls the experiment itself makes.

## Development

```bash
uv sync
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

## Ecosystem

kanon installs versioned configuration packages to `.packages/`. loadout applies a package to the local machine. token_miser benchmarks packages by running identical tasks under baseline (vanilla) and package configurations, then compares token usage, cost, and quality. Results can be published back to kanon so teams converge on the best-performing package.

```
kanon distributes  ->  loadout applies  ->  token-miser measures  ->  publish to kanon
(versioned packages)   (local config)       (A/B comparison)         (best package wins)
```
