# Implementation Plan

Hand-written from notes-mvp.md. Edit freely — the executor reads this file.

---

## Dependency Graph

```
STORY-001 (scaffold)
├── STORY-002 (task YAML)
├── STORY-003 (arm)
└── STORY-008 (db)

STORY-002 ──────────────────────────────────────────────┐
STORY-003 ───────────────────────────────────────────┐  │
                                                      │  │
STORY-004 (environment) ← needs STORY-002, STORY-003 │  │
                                                      │  │
STORY-005 (executor)    ← needs STORY-004             │  │
STORY-006 (checker)     ← needs STORY-002, STORY-004  │  │
STORY-007 (evaluator)   ← needs STORY-002              │  │
STORY-008 (db)          ← needs STORY-001              │  │
STORY-009 (report)      ← needs STORY-008              │  │
                                                        │  │
STORY-010 (cli wiring)  ← needs STORY-005..009          ┘  │
STORY-011 (synth-001)   ← standalone data file ────────────┘

BT-001 (build/vet)      ← needs all stories
BT-002 (smoke+mock)     ← needs STORY-010, STORY-011
```

**Recommended execution order (parallel waves):**

| Wave | Stories |
|------|---------|
| 1 | STORY-001 |
| 2 | STORY-002, STORY-003, STORY-008 |
| 3 | STORY-004, STORY-007, STORY-009, STORY-011 |
| 4 | STORY-005, STORY-006 |
| 5 | STORY-010 |
| 6 | BT-001, BT-002 |

---

## STORY-001 — Project scaffold

### User story
As a developer, I want the Go module initialized with a CLI skeleton so that subsequent stories have a compilable project to build on.

### Context
Greenfield Go project. Module path: `github.com/rubin-johnson/token_miser`. Entry point at `cmd/token-miser/main.go`. CLI uses stdlib `flag` with custom subcommand dispatch (no cobra).

### Acceptance criteria
1. `go build ./cmd/token-miser/` produces a `token-miser` binary.
2. `token-miser --help` exits 0 and output contains `run`, `compare`, `history`, `tasks`.
3. Each subcommand prints "not implemented" and exits 1.
4. `cmd/smoke_test.go` builds the binary, invokes `--help`, asserts exit 0 and subcommand names present.
5. `go vet ./...` passes.

### Files to create
- `go.mod` (via `go mod init`)
- `cmd/token-miser/main.go`
- `internal/cli/cli.go`
- `cmd/smoke_test.go`

---

## STORY-002 — Task YAML loading

### User story
As an experiment runner, I want to load task definitions from YAML files so that experiments are declarative and version-controlled.

### Context
Dep: `gopkg.in/yaml.v3`. Task struct has: ID, Name, Type (default "single_shot"), Repo, StartingCommit, Prompt, SuccessCriteria (typed), QualityRubric.

### Acceptance criteria
1. `LoadTask("testdata/valid.yaml")` returns a fully populated `*Task`.
2. `LoadTask("testdata/missing-id.yaml")` returns error containing "id".
3. `LoadTask("nonexistent.yaml")` returns error.
4. `Criterion` struct has typed fields: `Type string`, `Paths []string`, `Command string`, `Contains []string`.
5. `RubricDimension` struct has `Dimension string`, `Prompt string`.

### Files to create
- `internal/task/task.go`
- `internal/task/task_test.go`
- `internal/task/testdata/valid.yaml`
- `internal/task/testdata/missing-id.yaml`

---

## STORY-003 — Arm definition

### User story
As an experiment runner, I want to parse arm specifications from CLI arguments so that "vanilla" means no config and a path means a loadout bundle.

### Context
No external deps. Simple parsing: "vanilla" → empty loadout path; anything else → validate it's a directory.

### Acceptance criteria
1. `ParseArm("vanilla")` returns `Arm{Name: "vanilla", LoadoutPath: ""}`.
2. `ParseArm("/some/dir")` where dir exists returns `Arm{Name: "dir", LoadoutPath: "/some/dir"}`.
3. `ParseArm("/nonexistent")` returns error.
4. `ParseArm("/some/file")` where path is a file (not dir) returns error.

### Files to create
- `internal/arm/arm.go`
- `internal/arm/arm_test.go`

---

## STORY-004 — Environment setup

### User story
As an experiment runner, I want each arm to get an isolated HOME directory with a clean git checkout so that experiments don't contaminate each other or the host.

### Context
Depends on `internal/task` and `internal/arm`. Creates temp dir as HOME, clones repo with `--shared` for speed, checks out starting commit, optionally applies loadout. Uses a `Commander` interface so subprocess calls can be mocked in tests.

### Acceptance criteria
1. `SetupEnv` creates temp dir, clones repo, checks out commit.
2. For treatment arm, `loadout apply --target <home>/.claude --yes <bundle>` is called.
3. For vanilla arm, no loadout command is called.
4. `TeardownEnv` removes the entire temp dir.
5. Unit tests mock the Commander interface; assert correct commands and args.
6. Integration test (build tag `integration`): actually clones loadout repo at `fd88685`, verifies `docs/design-notes.md` exists in workspace.

### Files to create
- `internal/environment/environment.go`
- `internal/environment/environment_test.go`

---

## STORY-005 — Claude executor

### User story
As an experiment runner, I want to invoke Claude CLI in an isolated environment and capture token usage from its JSON output.

### Context
Depends on `internal/environment`. Pattern copied from `ralphael/internal/runner/runner.go`:
strip `CLAUDECODE` from env, set `HOME`, use `--print --dangerously-skip-permissions --output-format json --no-session-persistence`, prompt via stdin, parse JSON.

Claude JSON schema:
```json
{"result":"...","total_cost_usd":0.04,"usage":{"input_tokens":1200,"output_tokens":3400,"cache_creation_input_tokens":0,"cache_read_input_tokens":800}}
```

### Acceptance criteria
1. `ParseClaudeJSON` with valid JSON returns populated `ExecutorResult`.
2. `ParseClaudeJSON` with missing usage fields returns zero values (no error).
3. `ParseClaudeJSON` with invalid JSON returns error.
4. `FilterEnv` strips `CLAUDECODE` and sets `HOME`.
5. `RunClaude` measures wall time and populates `WallSeconds`.

### Files to create
- `internal/executor/executor.go`
- `internal/executor/executor_test.go`

---

## STORY-006 — Success criteria checker

### User story
As an experiment runner, I want to verify whether Claude's output satisfies the task's success criteria using automated checks.

### Context
Depends on `internal/task` (Criterion type) and `internal/environment` (EnvironmentContext). Runs commands in the workspace with HOME set. Three criterion types: `file_exists`, `command_exits_zero`, `output_contains`.

### Acceptance criteria
1. `file_exists`: passes when all paths exist; fails with detail listing missing paths.
2. `command_exits_zero`: passes on exit 0; fails with stderr captured in detail.
3. `output_contains`: passes when stdout contains all strings; fails with missing strings listed.
4. Each criterion evaluated independently — one failure doesn't skip others.
5. Commands run with `HOME=env.HomeDir` and `cwd=env.WorkspaceDir`.

### Files to create
- `internal/checker/checker.go`
- `internal/checker/checker_test.go`

---

## STORY-007 — Quality evaluator

### User story
As an experiment runner, I want an LLM judge to score the quality of Claude's output on multiple dimensions so that token savings can be weighed against quality.

### Context
Depends on `internal/task` (RubricDimension). Uses `github.com/anthropics/anthropic-sdk-go` to call Haiku as judge. Reads workspace files to build context for the judge prompt.

### Acceptance criteria
1. `NewEvaluator(apiKey)` creates evaluator with Anthropic client.
2. `ScoreQuality` returns one `DimensionScore` per rubric dimension.
3. Each score has `Score` (0.0-1.0) and `Reason` (non-empty string).
4. File collection skips hidden dirs, `vendor/`, `node_modules/`, `.git/`.
5. Unit tests mock the Anthropic client interface; verify prompt construction and JSON parsing.

### Files to create
- `internal/evaluator/evaluator.go`
- `internal/evaluator/evaluator_test.go`

---

## STORY-008 — SQLite storage

### User story
As an experiment runner, I want results stored in SQLite so that I can compare arms across runs.

### Context
Uses `modernc.org/sqlite` (pure Go, no cgo). DB at `~/.token_miser/results.db`. Creates dir if needed.

### Acceptance criteria
1. `InitDB` creates `runs` table with all columns from schema.
2. `StoreRun` inserts a run and returns its ID.
3. `GetRuns("")` returns all runs.
4. `GetRuns("synth-001")` returns only runs for that task.
5. `QualityScores` stored and retrieved as JSON string.
6. All tests use in-memory DB.

### Files to create
- `internal/db/db.go`
- `internal/db/db_test.go`

---

## STORY-009 — Report output

### User story
As a user, I want a side-by-side comparison of experiment arms showing tokens, cost, criteria pass rate, and quality scores.

### Context
Depends on `internal/db`. Plain text output (no color for MVP).

### Acceptance criteria
1. `Compare(taskID, db)` groups runs by arm.
2. Output shows per-arm: total tokens, cost, wall time, criteria pass/total, per-dimension quality scores.
3. With exactly two arms, output is side-by-side.
4. Tests use fixture `Run` slices; assert key strings appear in output.

### Files to create
- `internal/report/report.go`
- `internal/report/report_test.go`

---

## STORY-010 — CLI wiring

### User story
As a user, I want the CLI subcommands to work end-to-end, orchestrating the full experiment pipeline.

### Context
Depends on all prior stories. Wires together: LoadTask → SetupEnv → RunClaude → EvaluateCriteria → ScoreQuality → StoreRun → Compare. Uses `defer TeardownEnv` for cleanup.

### Acceptance criteria
1. `token-miser run --task <path> --control vanilla --treatment <path>` runs both arms and prints summary.
2. `token-miser compare --task <id>` prints comparison from DB.
3. `token-miser history` lists all runs with timestamps and totals.
4. `token-miser tasks --dir <dir>` lists YAML files with IDs and names.
5. `--model` flag defaults to "sonnet".
6. Smoke test: `token-miser tasks --dir tasks/` output contains "synth-001".

### Files to modify
- `internal/cli/cli.go`
- `cmd/smoke_test.go` (add tasks subcommand test)

---

## STORY-011 — synth-001 task definition

### User story
As a user, I want the first experiment task defined so that I can run a real vanilla-vs-loadout comparison.

### Context
Standalone data file. This task tests Claude's ability to scaffold a Python project (the loadout repo). The task prompt and success criteria reference the target project's toolchain — not token_miser's.

### Acceptance criteria
1. `tasks/synth-001.yaml` is valid YAML loadable by `LoadTask`.
2. Task targets `/home/rujohnson/code/personal/loadout` at commit `fd88685`.
3. Success criteria test for file existence, command exit codes, and output content.
4. Quality rubric covers structure, CLI completeness, TDD readiness, code quality.

### Files to create
- `tasks/synth-001.yaml`

---

## BT-001 — Full build and vet check

### User story
As a developer, I want the full project to build, vet, and pass all unit tests before considering MVP complete.

### Acceptance criteria
1. `go build ./...` exits 0.
2. `go vet ./...` exits 0.
3. `go test ./...` (excluding integration tag) exits 0.

---

## BT-002 — Smoke test with mocked Claude

### User story
As a developer, I want an end-to-end smoke test with a fake Claude binary so that the full pipeline is validated without real API calls.

### Context
Create a shell script that emits valid Claude JSON. Put it on PATH. Run `token-miser run` via subprocess.

### Acceptance criteria
1. Fake `claude` script in temp dir emits JSON with `result`, `total_cost_usd`, `usage` fields.
2. `token-miser run --task tasks/synth-001.yaml --control vanilla --treatment ./ --model sonnet` exits 0.
3. DB file exists after run.
4. `token-miser compare --task synth-001` produces output mentioning both "vanilla" and the treatment arm name.

### Files to modify
- `cmd/smoke_test.go`
