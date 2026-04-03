# token-miser

A/B test Claude Code configurations.

token-miser runs identical tasks under different Claude Code "arms" (configuration bundles) and measures token usage, cost, and quality. Compare a vanilla Claude Code setup against one with a custom CLAUDE.md, hooks, and tooling to see whether a configuration change is actually worth the overhead.

## Concepts

- **Task** — A YAML file describing work for Claude to do: a prompt, a target repo, success criteria, and a quality rubric.
- **Arm** — A Claude Code configuration bundle (a [loadout](https://github.com/rubin-johnson/loadout)) used to execute the task.
- **Run** — A single execution of a task under one arm.
- **Experiment** — A pair of runs (control + treatment arm) on the same task.

## Requirements

- Go 1.24+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- SQLite (bundled via CGo-free driver — no system install needed)

## Installation

```bash
go install github.com/rubin-johnson/token_miser/cmd/token-miser@latest
```

Initialize the database:

```bash
token-miser migrate
```

## Usage

### Run an experiment

```bash
token-miser run \
  --task tasks/synth-001.yaml \
  --control loadouts/experiment-config \
  --treatment loadouts/my-config \
  --model sonnet
```

Each arm executes the task in sequence. Results are stored in `~/.token_miser/results.db`.

### Compare results

```bash
# Side-by-side token/cost/quality comparison for a task
token-miser compare --task synth-001

# Statistical summary (mean, stddev, min/max per arm)
token-miser analyze --task synth-001
```

### Browse history

```bash
# List all runs
token-miser history

# Inspect a specific run
token-miser show <run-id>
```

### Manage tasks

```bash
# List task YAML files in a directory
token-miser tasks --dir tasks/
```

## Task format

```yaml
id: my-task
name: "Human-readable name"
repo: "/absolute/path/to/target/repo"   # Claude works here
starting_commit: "abc1234"              # repo is reset to this commit before each run
prompt: |
  What you want Claude to do...
success_criteria:
  - type: file_exists
    paths: ["some/file.py"]
  - type: command_exits_zero
    command: "uv run pytest"
quality_rubric:
  - dimension: "correctness"
    prompt: "Does the output satisfy the requirement? Score 0-100."
  - dimension: "code_quality"
    prompt: "Is the code idiomatic and clean? Score 0-100."
```

**Success criteria types**

| Type | Fields |
|------|--------|
| `file_exists` | `paths` — list of paths that must exist |
| `command_exits_zero` | `command` — shell command that must exit 0 |

Quality dimensions are scored 0–100 by a Claude judge. Final quality score is the mean across dimensions.

## Loadouts

Loadouts are Claude Code configuration bundles stored under `loadouts/`. Each is a directory with a `manifest.yaml` declaring which files to deploy into the target project's `.claude/` directory before each run.

See [`loadouts/experiment-config/`](loadouts/experiment-config/) for a working example.

**Keep personal loadouts out of version control.** Add your own loadout directories to `.gitignore` — commit only shared/example configs.

## Data

All results are stored locally in `~/.token_miser/results.db` (SQLite). Nothing is sent externally beyond the Claude API calls the experiment itself makes.

## Status

Pre-alpha. The core experiment loop works. See [docs/plans/critique-and-roadmap.md](docs/plans/critique-and-roadmap.md) for a candid assessment of current limitations and planned roadmap.
