# token-miser

A/B test coding-agent configurations.

token-miser runs identical tasks under different agent/package combinations and measures token usage, cost, and task-completion quality. It supports Claude Code and Codex from the same CLI, so you can compare a vanilla setup against a tuned package — across one agent or both.

## Benchmark Results

**[rubin-johnson.github.io/token_miser](https://rubin-johnson.github.io/token_miser)** — live dashboard with pass rates, token usage, and cost across packages and suites.

All experiment data is collected by the repo owner on a consistent setup. See [Submitting a package](#submitting-a-package-for-benchmarking) if you want your package included.

## Concepts

- **Task** — A YAML file describing work for an agent: a prompt, a target repo, success criteria, and a quality rubric.
- **Package** — A configuration directory with a `manifest.yaml` that bundles `CLAUDE.md`/`AGENTS.md`, optional `settings.json` (hooks, permissions), and optional services.
- **Suite** — A named collection of tasks (e.g. `quick`, `standard`, `axis`, `domain-python-api`).
- **Run** — A single execution of a task under one package.
- **Experiment** — One or more runs across baseline/package and agent combinations.

## Requirements

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated (`claude auth status`)
- [Codex CLI](https://developers.openai.com/codex/) installed and authenticated for Codex runs (`codex`)

## Install

```bash
uv tool install .
```

Or run directly:

```bash
uv run token-miser --help
```

## Quick start

The `tune` command is the primary workflow — it runs a suite of tasks against a baseline and one or more packages, then reports results:

```bash
# Run the quick suite (8 tasks) against the caveman package
token-miser tune --suite quick --package caveman --yes

# Test with both Claude and Codex
token-miser tune --suite quick --package caveman --agent both --yes

# Compare multiple packages across the axis suite
token-miser tune --suite axis --package c-structured --agent both --yes
```

For single-task experiments:

```bash
# Run one task against a package
token-miser run \
  --task benchmarks/tasks/bm-axis-explore.yaml \
  --baseline vanilla \
  --package caveman

# Compare results
token-miser compare --task bm-axis-explore

# Inspect a specific run
token-miser history
token-miser show 1
```

## Commands

| Command | Purpose |
|---------|---------|
| `tune` | Run a benchmark suite against baseline + package (primary workflow) |
| `run` | Execute a single task under baseline and/or package |
| `compare` | Side-by-side comparison of runs for a task |
| `analyze` | Statistical summary (mean, stdev, median per package) |
| `matrix` | Cross-package comparison grid (text + JSON export) |
| `history` | List all recorded runs |
| `show <id>` | Inspect a specific run in detail |
| `digest` | Export run data for git tracking |
| `suite` | List, validate, or pre-clone suite repos |
| `packages` / `list` | List available packages |
| `publish` | Publish a package to a git repo for kanon distribution |
| `tasks` | List available task YAML files |
| `migrate` | Initialize or migrate the database |

### tune

```bash
token-miser tune \
  --suite axis \
  --package caveman \
  --agent both \
  --model sonnet \
  --timeout 600 \
  --yes
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--suite` | `standard` | Benchmark suite name |
| `--package` | (optional) | Package to test: name or path |
| `--agent` | `claude` | `claude`, `codex`, `openai` (alias), or `both` |
| `--model` | agent-specific | Claude defaults to `sonnet`; Codex to `gpt-5.4` |
| `--timeout` | `600` | Per-task timeout in seconds |
| `--skip-baseline` | off | Reuse the last baseline run |
| `--bare` | off | Skip hooks/plugins (cheaper, less realistic) |
| `--yes` | off | Skip confirmation prompts |

### run

```bash
token-miser run \
  --task benchmarks/tasks/bm-axis-explore.yaml \
  --baseline vanilla \
  --package caveman \
  --agent codex \
  --timeout 600
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--task` | (required) | Path to task YAML |
| `--baseline` | (required) | Baseline: `vanilla`, package name, or path |
| `--package` | (optional) | Package to test: name or path |
| `--agent` | `claude` | `claude`, `codex`, `openai` (alias), or `both` |
| `--model` | agent-specific | Claude defaults to `sonnet`; Codex to `gpt-5.4` |
| `--timeout` | `600` | Per-invocation timeout in seconds |

### Global flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--packages-dir` | `$TOKEN_MISER_PACKAGES_DIR` or `./packages` | Directory containing packages |

Package names (no `/`) resolve to `{packages-dir}/{name}/`. Paths with `/` are used as-is.

## Suites

Six benchmark suites ship in `benchmarks/suites/`:

| Suite | Tasks | Focus |
|-------|-------|-------|
| `quick` | 8 | Fast screening |
| `standard` | 15 | General-purpose benchmark |
| `axis` | 8 | Interaction patterns (explore, multiturn, diff, testrun, bashheavy, smallio, reasoning, bigoutput) |
| `domain-python-api` | 8 | Python API development |
| `domain-iac` | 8 | Infrastructure as code |
| `domain-frontend` | 8 | Frontend development |

```bash
token-miser suite list         # show available suites
token-miser suite validate     # check all task YAMLs are valid
token-miser suite prep         # pre-clone repos to speed up runs
```

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
4. Apply the selected package (copy targets, deep-merge `settings.json`)
5. Invoke the selected backend:
   - Claude: `claude --print --dangerously-skip-permissions --output-format json`
   - Codex: `codex exec --json --sandbox workspace-write --full-auto`
6. Check success criteria against the workspace
7. Optionally score quality via Claude-as-judge (requires `ANTHROPIC_API_KEY`)
8. Store results in SQLite (`~/.token_miser/results.db`)

## Packages

24 packages ship in `packages/`, spanning different optimization strategies:

| Package | Strategy |
|---------|----------|
| `caveman` | Minimal tool use, think before acting |
| `c-structured` | Structured output, systematic approach |
| `tdd-strict` | Strict TDD — failing test first, always |
| `thorough` | Maximize correctness — read everything, explain reasoning |
| `token-miser` | Minimize tokens — terse output, lazy reads, no extras |
| `lean` | Minimal overhead, skip unnecessary steps |
| `rtk` | Rust CLI hook that compresses verbose command outputs |
| ... | See `token-miser list` for all 24 |

Each package is a directory with a `manifest.yaml`:

```yaml
name: my-package
version: 0.1.0
author: your-name
description: What this package does
targets:
  - path: AGENTS.md
    dest: AGENTS.md
  - path: settings.json    # optional — deep-merged into experiment config
    dest: settings.json
```

Packages can include `CLAUDE.md`/`AGENTS.md` instructions, `settings.json` for hooks and permissions, and hook scripts. The `settings.json` is deep-merged with any existing experiment configuration rather than overwriting it.

To use packages from another directory:

```bash
export TOKEN_MISER_PACKAGES_DIR=~/.claude/packages
token-miser list
token-miser tune --package lean
```

### Shared instructions

Codex uses `AGENTS.md`. Claude Code uses `CLAUDE.md`. To share one instruction file across agents, use the `@AGENTS.md` import pattern in `CLAUDE.md`:

```md
# CLAUDE.md
@AGENTS.md
```

## Matrix runs

For package screening across a benchmark suite:

```bash
SUITE=quick REPEATS=1 AGENTS=claude,codex \
  ./scripts/run-suite-shared-baseline.sh
```

Runs one shared `vanilla` baseline per `agent x repeat x suite`, then reuses it across packages.

For stricter order-balanced comparisons:

```bash
SUITE=quick REPEATS=2 AGENTS=claude,codex \
  ./scripts/run-suite-crossover.sh
```

Alternates baseline/package order by repeat to control for run-to-run drift.

## Data

All results are stored locally in `~/.token_miser/results.db` (SQLite). Runs record the agent backend, so Claude and Codex experiments coexist in the same history and reports.

```bash
token-miser history            # compact list of all runs
token-miser show 12            # full token breakdown for one run
token-miser matrix --suite axis --json results.json   # export comparison grid
```

## Development

```bash
git clone https://github.com/rubin-johnson/token_miser.git
cd token_miser
uv sync
uv run pytest -q              # 198 tests
uv run token-miser --help
```

## Submitting a package for benchmarking

All benchmark data is collected by me (Rubin Johnson) on a consistent hardware and model setup. I don't accept self-reported numbers — I run all experiments myself so results are comparable.

**To submit a package:**

1. Open a GitHub issue titled `benchmark request: <package-name>`
2. Include your package files (`CLAUDE.md` / `AGENTS.md`, optional `settings.json`, optional hooks)
3. Describe the strategy in 2-3 sentences: what behavior it changes and why
4. Include reproduction details: model, suite, any env requirements
5. If you have your own numbers, include them — I'll run independently and compare

Packages that test a genuinely new strategy dimension are most likely to get picked up.

If your package is already in a [kanon](https://github.com/rubin-johnson/kanon) registry, link to it in the issue.

## Ecosystem

[kanon](https://github.com/rubin-johnson/kanon) distributes versioned configuration packages. token-miser benchmarks them by running identical tasks under baseline and package configurations, then comparing token usage, cost, and quality. Results can be published back to kanon so teams converge on the best-performing package.

```
kanon distributes  ->  token-miser measures  ->  publish to kanon
(versioned packages)   (A/B comparison)         (best package wins)
```
