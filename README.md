# token-miser

A/B test coding-agent configurations.

token-miser runs identical tasks under different agent/package combinations and measures token usage, cost, and quality. It supports both Claude Code and Codex runs from the same CLI, so you can compare a vanilla setup against a package, across one agent or both.

## Benchmark Results

**[rubin-johnson.github.io/token_miser](https://rubin-johnson.github.io/token_miser)** — live results dashboard showing pass rates, token usage, and cost across packages and suites.

Current headline (standard suite, 15 tasks, Claude Sonnet 4.6 via Bedrock):

| Package | Pass rate | Tokens | vs baseline |
|---------|-----------|--------|-------------|
| baseline (vanilla) | 12% | 85,957 | — |
| rubin | **40%** | 79,255 | -7.8% tokens |
| rubin-lazy | 36% | 76,773 | -10.7% tokens |
| rubin-async | 32% | 76,352 | -11.2% tokens |

All experiment data is collected by the repo owner on a consistent setup. See [Submitting a package](#submitting-a-package-for-benchmarking) if you want your package included.

## Concepts

- **Task** -- A YAML file describing work for an agent to do: a prompt, a target repo, success criteria, and a quality rubric.
- **Package** -- A configuration package (a [loadout](https://github.com/rubin-johnson/loadout)) used to influence the run.
- **Run** -- A single execution of a task under one package.
- **Experiment** -- One or more runs across baseline/package and agent combinations.

## Requirements

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated for Claude runs (`claude auth status`)
- [Codex CLI](https://developers.openai.com/codex/) installed and authenticated for Codex runs (`codex`)
- [loadout](https://github.com/rubin-johnson/loadout) — installed automatically as a dependency (git source)

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
git clone https://github.com/rubin-johnson/token_miser.git
cd token_miser
uv sync
uv run token-miser --help
```

> **Note:** The `loadout` dependency is declared as a git source in `pyproject.toml`. Do not
> run `pip install loadout` separately — the package with that name on PyPI is unrelated.
> `uv sync` handles the correct version automatically.

## Submitting a package for benchmarking

All benchmark data is collected by me (Rubin Johnson) on a consistent hardware and model setup. I don't accept self-reported numbers — I run all experiments myself so results are comparable.

**To submit a package:**

1. Open a GitHub issue titled `benchmark request: <package-name>`
2. Include your package files (`CLAUDE.md` / `AGENTS.md`, optional `settings.json`)
3. Describe the strategy in 2–3 sentences: what behavior it changes and why
4. Include reproduction details: model, suite, any env requirements
5. If you have your own numbers, include them with your setup — I'll run independently and compare

Packages that test a genuinely new strategy dimension are most likely to get picked up. I'll decline submissions that duplicate existing ones or can't be run cleanly in the standard environment.

If your package is already in the [loadout-packages registry](https://github.com/rubin-johnson/loadout-packages), just link to it in the issue.

Caylent colleagues may get access to run experiments directly — reach out if interested.

## Ecosystem

kanon installs versioned configuration packages to `.packages/`. loadout applies a package to the local machine. token_miser benchmarks packages by running identical tasks under baseline (vanilla) and package configurations, then compares token usage, cost, and quality. Results can be published back to kanon so teams converge on the best-performing package.

```
kanon distributes  ->  loadout applies  ->  token-miser measures  ->  publish to kanon
(versioned packages)   (local config)       (A/B comparison)         (best package wins)
```
