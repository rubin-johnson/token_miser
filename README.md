# token-miser

A/B test Claude Code configurations.

token-miser runs identical tasks under different Claude Code "arms" (configuration bundles) and measures token usage, cost, and quality. Compare a vanilla Claude Code setup against one with a custom CLAUDE.md, hooks, and tooling to see whether a configuration change is actually worth the overhead.

## Concepts

- **Task** -- A YAML file describing work for Claude to do: a prompt, a target repo, success criteria, and a quality rubric.
- **Arm** -- A Claude Code configuration bundle (a [loadout](https://github.com/rubin-johnson/loadout)) used to execute the task.
- **Run** -- A single execution of a task under one arm.
- **Experiment** -- A pair of runs (control + treatment arm) on the same task.

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

# Run an experiment: vanilla (no config) vs. a loadout bundle
token-miser run \
  --task tasks/synth-001.yaml \
  --control vanilla \
  --treatment loadouts/experiment-config

# Compare the results
token-miser compare --task synth-001

# Statistical analysis
token-miser analyze --task synth-001
```

## Commands

| Command | Purpose |
|---------|---------|
| `run` | Execute a task under control and/or treatment arms |
| `compare` | Side-by-side comparison of runs for a task |
| `analyze` | Statistical summary (mean, stdev, median per arm) |
| `history` | List all recorded runs |
| `show <id>` | Inspect a specific run in detail |
| `tasks` | List available task YAML files |
| `migrate` | Initialize or migrate the database |

### run

```bash
token-miser run \
  --task tasks/synth-001.yaml \
  --control vanilla \
  --treatment loadouts/experiment-config \
  --model sonnet \
  --timeout 600
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--task` | (required) | Path to task YAML |
| `--control` | (required) | Control arm: `vanilla` or path to loadout bundle |
| `--treatment` | (optional) | Treatment arm: path to loadout bundle |
| `--model` | `sonnet` | Model identifier for metadata |
| `--timeout` | `600` | Per-invocation timeout in seconds |

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

For each arm in an experiment:

1. Create an isolated temp directory as `HOME`
2. Clone the task's target repo and checkout the starting commit
3. Copy Claude credentials into the isolated HOME
4. If treatment arm: run `loadout apply` to deploy the configuration bundle
5. Invoke `claude --print --dangerously-skip-permissions --output-format json`
6. Check success criteria against the workspace
7. Optionally score quality via Claude-as-judge (requires `ANTHROPIC_API_KEY`)
8. Store results in SQLite (`~/.token_miser/results.db`)

## Relationship with loadout and kanon

**[loadout](https://github.com/rubin-johnson/loadout)** manages Claude Code configuration bundles. token-miser uses loadout to deploy treatment arms into isolated test environments.

**[kanon](https://github.com/caylent-solutions/kanon)** distributes versioned packages across teams. Loadout bundles can be distributed as kanon packages, giving teams a pipeline: kanon distributes versioned bundles, loadout applies them, token-miser measures whether they improve performance.

## Data

All results stored locally in `~/.token_miser/results.db` (SQLite). Nothing is sent externally beyond the Claude API calls the experiment itself makes.

## Development

```bash
uv sync
uv run pytest tests/ -v
uv run ruff check src/ tests/
```
