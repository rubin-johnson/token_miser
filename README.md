# token-miser

A/B test coding-agent configurations.

token-miser runs identical tasks under different agent/package combinations and measures token usage, cost, and quality. It now supports both Claude Code and Codex runs from the same CLI, so you can compare a vanilla setup against a package, across one agent or both.

## Concepts

- **Task** -- A YAML file describing work for an agent to do: a prompt, a target repo, success criteria, and a quality rubric.
- **Package** -- A configuration package (a [loadout](https://github.com/rubin-johnson/loadout)) used to influence the run.
- **Run** -- A single execution of a task under one package.
- **Experiment** -- One or more runs across baseline/package and agent combinations.

## Requirements

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated for Claude runs (`claude auth status`)
- [Codex CLI](https://developers.openai.com/codex/) installed and authenticated for Codex runs (`codex`)
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

# Run a Claude experiment
token-miser run \
  --agent claude \
  --task tasks/synth-001.yaml \
  --baseline vanilla \
  --package token-miser

# Run a Codex experiment
token-miser run \
  --agent codex \
  --task tasks/synth-001.yaml \
  --baseline vanilla \
  --package token-miser

# Run both backends in one command
token-miser run \
  --agent both \
  --task tasks/synth-001.yaml \
  --baseline vanilla \
  --package token-miser

# Compare the results
token-miser compare --task synth-001

# Inspect token usage for a specific run
token-miser history
token-miser show 1
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
  --agent codex \
  --task tasks/synth-001.yaml \
  --baseline vanilla \
  --package token-miser \
  --model gpt-5.4 \
  --timeout 600
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--task` | (required) | Path to task YAML |
| `--baseline` | (required) | Baseline: `vanilla`, package name, or path |
| `--package` | (optional) | Package to test: name or path |
| `--agent` | `claude` | `claude`, `codex`, `openai` (alias for Codex), or `both` |
| `--model` | agent-specific | Claude defaults to `sonnet`; Codex defaults to `gpt-5.4` |
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
  What you want the agent to do...
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

For each run in an experiment:

1. Create an isolated temp directory as `HOME`
2. Clone the task's target repo and checkout the starting commit
3. Copy the selected agent's auth/config into the isolated HOME
4. Apply or translate the selected package for that backend
5. Invoke the selected backend:
   - Claude: `claude --print --dangerously-skip-permissions --output-format json`
   - Codex: `codex exec --json --sandbox workspace-write --full-auto`
6. Check success criteria against the workspace
7. Optionally score quality via Claude-as-judge (requires `ANTHROPIC_API_KEY`)
8. Store results in SQLite (`~/.token_miser/results.db`)

## Seeing Token Usage

During `run`, token_miser prints input, output, cached, cost, wall time, criteria, and run ID in the summary.

After a run:

```bash
token-miser history   # compact list of recorded runs
token-miser show 12   # full token breakdown for one run
```

`show` includes agent, model, input tokens, output tokens, cached tokens, reasoning tokens when available, and total cost.

## Matrix Runs

For package screening across a benchmark suite:

```bash
SUITE=quick REPEATS=1 AGENTS=claude,codex MODEL=gpt-5.4-mini \
  ./scripts/run-suite-shared-baseline.sh
```

That mode runs one shared `vanilla` baseline per `agent x repeat x suite`, then reuses it across packages.

For stricter order-balanced comparisons:

```bash
SUITE=quick REPEATS=2 AGENTS=claude,codex MODEL=gpt-5.4 \
  ./scripts/run-suite-crossover.sh
```

That mode runs each `package` against `vanilla` task-by-task and alternates order by repeat:
- odd repeats: `vanilla -> package`
- even repeats: `package -> vanilla`

Shared baseline is the cheap screening pass. Crossover is slower but controls better for order effects and run-to-run drift.

## Shared Instructions

Codex uses `AGENTS.md`. Claude Code uses `CLAUDE.md`. To keep one canonical instruction file, token_miser now supports the pattern:

```md
# CLAUDE.md
@AGENTS.md
```

Generated tuned packages now write shared instructions to `AGENTS.md` and keep `CLAUDE.md` as a shim import.

## Packages

Packages ship in `packages/` and can be referenced by name:

| Package | Philosophy |
|---------|-----------|
| `token-miser` | Minimize tokens -- terse output, lazy reads, no extras |
| `thorough` | Maximize correctness -- read everything, explain reasoning |
| `tdd-strict` | Strict TDD -- failing test first, always |

Each is a valid loadout package with a `manifest.yaml`. Claude-oriented packages can still ship `CLAUDE.md`; tuned packages generated by token_miser now use `AGENTS.md` plus a `CLAUDE.md` shim.

To use packages from another directory (e.g. your dotfiles):

```bash
export TOKEN_MISER_PACKAGES_DIR=~/.claude/packages
token-miser list           # show available packages
token-miser tune --package lean   # resolve by name
```

## Data

All results are stored locally in `~/.token_miser/results.db` (SQLite). Runs now record the agent backend as well, so Claude and Codex experiments can coexist in the same history and reports.

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
