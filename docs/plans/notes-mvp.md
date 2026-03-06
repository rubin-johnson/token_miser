# token_miser MVP — Implementation Notes

## What we're building

A Go CLI tool that runs controlled experiments comparing two Claude Code configurations
(arms) on a defined task. Measures token usage and quality. MVP supports a single
experiment type: single-shot task (one `claude --print` invocation per arm).

The two arms for the first real experiment:
- **control**: vanilla Claude (no ~/.claude/ config at all)
- **treatment**: user's current loadout bundle

---

## Architecture decisions (non-negotiable)

- **Language**: Go (go mod, go vet, golangci-lint before commit)
- **Config isolation**: each arm gets a temp dir as HOME; Claude reads `$HOME/.claude/`
- **Git isolation**: `git clone --shared <repo> $TMPDIR/workspace` then checkout commit
- **Claude invocation**: strip `CLAUDECODE` from subprocess env; use `--print
  --dangerously-skip-permissions --output-format json`; prompt via stdin; parse JSON result
- **Claude JSON schema** (confirmed from ralphael's runner.go):
  `result`, `total_cost_usd`, `usage.{input_tokens, output_tokens,
  cache_creation_input_tokens, cache_read_input_tokens}`
- **Storage**: SQLite via `modernc.org/sqlite` (pure Go, no cgo); DB at
  `~/.token_miser/results.db`
- **Quality evaluation**: LLM-as-judge via `github.com/anthropics/anthropic-sdk-go`;
  per-dimension 0.0–1.0 scores with reasoning; Haiku model
- **YAML parsing**: `gopkg.in/yaml.v3`
- **No Docker, no promptfoo for MVP**

---

## Project structure

```
token_miser/
  cmd/
    token-miser/
      main.go          # entry point, calls cli.Run()
  internal/
    cli/
      cli.go           # flag-based CLI: run, compare, history, tasks
    task/
      task.go          # Task struct, LoadTask()
      task_test.go
      testdata/        # YAML fixtures for tests
    arm/
      arm.go           # Arm struct, ParseArm()
      arm_test.go
    environment/
      environment.go   # EnvironmentContext, SetupEnv(), TeardownEnv()
      environment_test.go
    executor/
      executor.go      # RunClaude(), ParseClaudeJSON()
      executor_test.go
    checker/
      checker.go       # EvaluateCriteria()
      checker_test.go
    evaluator/
      evaluator.go     # ScoreQuality(), LLM-as-judge
      evaluator_test.go
    db/
      db.go            # InitDB(), StoreRun(), GetRuns()
      db_test.go
    report/
      report.go        # Compare(), FormatSummary()
      report_test.go
  tasks/
    synth-001.yaml     # first experiment (tests a Python project — see note below)
  go.mod
  go.sum
  cmd/smoke_test.go    # subprocess smoke tests
```

---

## Important: experiment subjects vs token_miser itself

token_miser is a Go project. But the tasks it runs experiments on can target any
language. synth-001 tests Claude's ability to scaffold a Python project (the loadout
repo). The task YAML's prompt, success criteria, and quality rubric reference the
target project's toolchain — not token_miser's.

---

## Story breakdown

### STORY-001: Project scaffold

Initialize Go module and CLI skeleton:
- `go mod init github.com/rubin-johnson/token_miser`
- `cmd/token-miser/main.go`: calls `cli.Run(os.Args)`
- `internal/cli/cli.go`: flag-based CLI with subcommands `run`, `compare`, `history`,
  `tasks` — all stubs returning `fmt.Errorf("not implemented")`
- `cmd/smoke_test.go`: build binary, invoke `token-miser --help`, assert exit 0 and
  output contains all four subcommand names; use `runTokenMiser` helper that builds
  binary into temp dir
- `go build ./...` must succeed; smoke test must pass

### STORY-002: Task YAML loading

Implement `internal/task/task.go`:
- `Task` struct with fields: `ID`, `Name`, `Type` (default `"single_shot"`), `Repo`,
  `StartingCommit`, `Prompt`, `SuccessCriteria` ([]Criterion with Type and typed fields),
  `QualityRubric` ([]RubricDimension with Dimension and Prompt strings)
- `Criterion` struct with `Type string` and fields for each type:
  - `Paths []string` (for file_exists)
  - `Command string` (for command_exits_zero, output_contains)
  - `Contains []string` (for output_contains)
- `LoadTask(path string) (*Task, error)`: read file, unmarshal YAML, validate required
  fields (ID, Repo, StartingCommit, Prompt); return descriptive error listing missing fields
- Add dep: `go get gopkg.in/yaml.v3`
- Tests in `internal/task/task_test.go`:
  - Load valid YAML fixture, assert all fields populated
  - Load invalid YAML (missing ID), assert error contains "id"
  - Load nonexistent file, assert error
- Fixtures: `internal/task/testdata/valid.yaml`, `internal/task/testdata/missing-id.yaml`

### STORY-003: Arm definition

Implement `internal/arm/arm.go`:
- `Arm` struct: `Name string`, `LoadoutPath string` (empty = vanilla)
- `ParseArm(spec string) (*Arm, error)`:
  - `"vanilla"` → `&Arm{Name: "vanilla", LoadoutPath: ""}`
  - anything else → stat the path; if not a directory return error; return
    `&Arm{Name: filepath.Base(path), LoadoutPath: path}`
- Tests: vanilla spec, valid directory spec, nonexistent path returns error,
  file (not dir) path returns error

### STORY-004: Environment setup

Implement `internal/environment/environment.go`:
- `EnvironmentContext` struct: `HomeDir string`, `WorkspaceDir string`
- `SetupEnv(task *task.Task, arm *arm.Arm) (*EnvironmentContext, error)`:
  1. `os.MkdirTemp("", "token-miser-*")` → `homeDir`
  2. `git clone --shared <task.Repo> <homeDir>/workspace` via `exec.Command`
  3. `git -C <workspace> checkout <task.StartingCommit>` via `exec.Command`
  4. If `arm.LoadoutPath != ""`:
     `loadout apply --target <homeDir>/.claude --yes <arm.LoadoutPath>` via `exec.Command`
  5. Return `&EnvironmentContext{HomeDir: homeDir, WorkspaceDir: homeDir+"/workspace"}`
- `TeardownEnv(ctx *EnvironmentContext) error`: `os.RemoveAll(ctx.HomeDir)`
- Unit tests: inject a `Commander` interface so exec calls can be mocked.
  Test that correct commands are called with correct arguments.
- Integration test (`//go:build integration`): actually clone loadout repo at fd88685,
  verify workspace exists with `docs/design-notes.md`

### STORY-005: Claude executor

Implement `internal/executor/executor.go`:
- `ExecutorResult` struct: `ResultText string`, `InputTokens int`, `OutputTokens int`,
  `CacheReadTokens int`, `CacheWriteTokens int`, `TotalCostUSD float64`,
  `WallSeconds float64`, `ExitCode int`
- `claudeJSON` struct matching the JSON schema (same as ralphael's runner.go)
- `ParseClaudeJSON(raw string) (*ExecutorResult, error)`: unmarshal JSON, populate
  ExecutorResult; if JSON invalid return error with raw string excerpt
- `RunClaude(ctx context.Context, prompt string, env *environment.EnvironmentContext,
  model string) (*ExecutorResult, error)`:
  1. Write prompt to temp file in env.HomeDir
  2. Build env slice: copy `os.Environ()`, filter out `CLAUDECODE=*`, set
     `HOME=env.HomeDir`
  3. `cmd := exec.CommandContext(ctx, "claude", "--print",
     "--dangerously-skip-permissions", "--output-format", "json",
     "--model", model, "--no-session-persistence")`
  4. `cmd.Stdin` = opened prompt file; `cmd.Dir` = env.WorkspaceDir; `cmd.Env` = filtered env
  5. Record start time, run, record elapsed
  6. Call `ParseClaudeJSON(stdout)`; set `WallSeconds` and `ExitCode`; return result
- Tests: unit test `ParseClaudeJSON` with fixture JSON strings (happy path, missing
  usage fields, invalid JSON). Separate unit test for env filtering logic.

### STORY-006: Success criteria checker

Implement `internal/checker/checker.go`:
- `CriterionResult` struct: `Type string`, `Passed bool`, `Detail string`
- `EvaluateCriteria(criteria []task.Criterion, env *environment.EnvironmentContext) []CriterionResult`
  Supported criterion types:
  - `file_exists`: check each path in `Paths` exists under `env.WorkspaceDir`
  - `command_exits_zero`: run `Command` in shell in `env.WorkspaceDir` with
    `HOME=env.HomeDir` in env; pass if exit code 0; capture stderr for detail on fail
  - `output_contains`: run `Command`, check stdout contains all strings in `Contains`
- Each criterion evaluated independently; capture errors as failures, not panics
- Tests: use `t.TempDir()` for file_exists; mock exec for command types

### STORY-007: Quality evaluator

Implement `internal/evaluator/evaluator.go`:
- `DimensionScore` struct: `Dimension string`, `Score float64`, `Reason string`
- `Evaluator` struct with Anthropic client; `NewEvaluator(apiKey string) *Evaluator`
- `ScoreQuality(ctx context.Context, rubric []task.RubricDimension, taskPrompt string,
  workspaceDir string) ([]DimensionScore, error)`
  For each dimension:
  1. Read relevant files from workspace (up to 5 files, max 4000 chars each) using
     `filepath.WalkDir`; skip hidden dirs and common non-source dirs (vendor, node_modules)
  2. Build judge prompt: system = "You are a code quality judge. Respond only with JSON.",
     user = task description + produced code excerpt + rubric dimension question +
     "Respond with {\"score\": 0.0-1.0, \"reason\": \"...\"}"
  3. Call Anthropic API (`github.com/anthropics/anthropic-sdk-go`) with
     `claude-haiku-4-5-20251001`; parse JSON response
  4. Append `DimensionScore`
- Tests: mock Anthropic client via interface; test prompt construction; test JSON parse

Add dep: `go get github.com/anthropics/anthropic-sdk-go`

### STORY-008: SQLite storage

Implement `internal/db/db.go`:
- DB path default: `filepath.Join(os.UserHomeDir(), ".token_miser", "results.db")`
- `InitDB(path string) (*sql.DB, error)`: open DB, create `runs` table if not exists
- `Run` struct mirroring schema; `QualityScores` stored as JSON string
- `StoreRun(db *sql.DB, run *Run) (int64, error)`
- `GetRuns(db *sql.DB, taskID string) ([]*Run, error)` (empty taskID = all runs)
- Schema:
  ```sql
  CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    arm TEXT NOT NULL,
    loadout_name TEXT,
    model TEXT,
    started_at TEXT,
    wall_seconds REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    total_cost_usd REAL,
    exit_code INTEGER,
    criteria_pass INTEGER,
    criteria_total INTEGER,
    quality_scores TEXT
  )
  ```
- Add dep: `go get modernc.org/sqlite`
- Tests: use in-memory DB; test InitDB creates table; test StoreRun/GetRuns roundtrip;
  test GetRuns filters by task_id

### STORY-009: Report output

Implement `internal/report/report.go`:
- `Compare(taskID string, db *sql.DB) (string, error)`: fetch runs for task, group by
  arm, format side-by-side table showing tokens, cost, criteria pass rate, quality scores
- `FormatRunSummary(runs []*db.Run) string`: helper for single arm summary
- Output is plain text (no color for MVP)
- Tests: create fixture Run slices, assert key strings appear in Compare output

### STORY-010: CLI wiring

Wire up `internal/cli/cli.go` fully:
- `token-miser run --task <path> --control <arm> --treatment <arm> [--model <model>]`
  Orchestrates: LoadTask → SetupEnv (both arms) → RunClaude → EvaluateCriteria →
  ScoreQuality → StoreRun → print summary for each arm → TeardownEnv
  Use `defer TeardownEnv` so cleanup happens even on error.
- `token-miser compare --task <task-id>`: open DB, Compare(), print
- `token-miser history [--task <task-id>]`: GetRuns(), print timestamps + token totals
- `token-miser tasks [--dir <dir>]`: glob `*.yaml` in tasks dir (default `./tasks/`),
  print IDs and names
- Update smoke test: verify `token-miser tasks` lists synth-001

### STORY-011: synth-001 task definition

Write `tasks/synth-001.yaml` — the first experiment task. NOTE: this task tests
Claude's ability to scaffold a Python project (the loadout repo). The task prompt
and success criteria reference the target project's toolchain, not token_miser's.

```yaml
id: synth-001
name: scaffold-loadout-package
repo: /home/rujohnson/code/personal/loadout
starting_commit: fd88685
prompt: |
  Read docs/design-notes.md. Scaffold this project as a Python package:
  pyproject.toml with hatchling build backend, a loadout CLI entry point
  using argparse with subcommands (validate, apply, restore, capture, status),
  stub modules for each command that raise NotImplementedError, and a test
  file that verifies help output and subcommand availability.
success_criteria:
  - type: file_exists
    paths:
      - pyproject.toml
      - tests/test_scaffold.py
  - type: command_exits_zero
    command: "pip install -e . && python -m loadout --help"
  - type: output_contains
    command: "python -m loadout --help"
    contains: [validate, apply, restore, capture, status]
quality_rubric:
  - dimension: structure
    prompt: "Does the package use proper Python layout with hatchling build backend?"
  - dimension: cli_completeness
    prompt: "Are all 5 subcommands (validate, apply, restore, capture, status) present and reachable?"
  - dimension: tdd_readiness
    prompt: "Do stubs raise NotImplementedError and do the tests provide meaningful coverage?"
  - dimension: code_quality
    prompt: "Is the code idiomatic without over-engineering or excessive comments?"
```

### BT-001: Full build and vet check

```
go build ./...
go vet ./...
go test ./... (non-integration)
```
All must pass.

### BT-002: Smoke with mocked Claude

Integration-style test in `cmd/smoke_test.go` with Claude subprocess stubbed:
set `PATH` to a temp dir containing a fake `claude` shell script that emits valid JSON
matching the claude JSON schema; run `token-miser run --task tasks/synth-001.yaml
--control vanilla --treatment ./` via subprocess; verify exit 0, DB file created,
`token-miser compare` produces output mentioning both arms.

---

## Dependencies

```
gopkg.in/yaml.v3
modernc.org/sqlite
github.com/anthropics/anthropic-sdk-go
```

## Notes for the agent

- token_miser is a Go project. Never create `.py` files in this repo.
- Experiment tasks can target projects in any language. synth-001 targets a
  Python project — that's the experiment subject, not token_miser's toolchain.
- Never touch `~/.claude/` directly — all operations use temp HOME dirs
- `loadout` is an external CLI tool that must be on PATH. token_miser invokes it
  via `exec.Command("loadout", ...)` — it does not import or embed loadout.
- All subprocess calls must filter `CLAUDECODE` from env (nested session protection)
- Tests never make real Claude API calls or real git operations unless tagged
  with `//go:build integration`
- `go test ./...` must pass before each commit
- Run `go vet ./...` before every commit; run `golangci-lint run` if available
- Follow existing patterns in `~/code/personal/ralphael` — same author, same conventions
- Error handling: always check errors, wrap with `fmt.Errorf("context: %w", err)`
