# CLI Wiring — notes for ralphael

## Context

All internal packages are implemented and tested:
- `internal/task` — LoadTask, Task struct (Repo, StartingCommit, Prompt, SuccessCriteria, QualityRubric)
- `internal/arm` — ParseArm (vanilla → empty LoadoutPath; path → Arm{Name, LoadoutPath})
- `internal/environment` — SetupEnv(task, arm, commander) → *EnvironmentContext{HomeDir, WorkspaceDir}; TeardownEnv
- `internal/executor` — RunClaude(prompt, homeDir) → *ExecutorResult{Result, TotalCostUSD, Usage{InputTokens,OutputTokens,...}, WallSeconds}; FilterEnv
- `internal/checker` — New(env) → Checker; CheckAllCriteria([]Criterion) → []CheckResult{Passed,Detail}
- `internal/evaluator` — NewEvaluator(apiKey); ScoreQuality(ctx, input, output, []RubricDimension) → []DimensionScore
- `internal/db` — InitDB(path) → *DB; StoreRun(*Run) → id; GetRuns(taskID) → []Run
- `internal/report` — Compare(taskID, *sql.DB) → string
- `internal/cli` — Dispatch(command, args); tasksCommand is implemented; run/compare/history are stubs

## Goal

Wire up `internal/cli/cli.go` so the three stub commands work end-to-end.

## run command

Flags: `--task <path>`, `--control <arm>`, `--treatment <arm>`, `--model <model>` (default "sonnet")

Pipeline for each arm (run both arms, sequentially is fine):
1. task.LoadTask(taskFile)
2. arm.ParseArm(armSpec)
3. environment.SetupEnv(task, &arm, environment.NewDefaultCommander())
4. defer env.TeardownEnv()
5. executor.RunClaude(task.Prompt, env.HomeDir) → result
6. checker.New(env).CheckAllCriteria(task.SuccessCriteria) → checkResults
7. Count pass/total from checkResults
8. evaluator.NewEvaluator(os.Getenv("ANTHROPIC_API_KEY")).ScoreQuality(ctx, task.Prompt, result.Result, task.QualityRubric) → scores
   - If ANTHROPIC_API_KEY is empty, skip quality scoring (scores = nil, no error)
9. Build db.Run from results; marshal quality scores to JSON string
10. db.InitDB(dbPath()) where dbPath = ~/.token_miser/results.db
11. db.StoreRun(&run)

After both arms: print a brief per-arm summary (arm name, tokens, cost, criteria pass/total).

DefaultCommander must be a real implementation using os/exec (the current one panics).

## compare command

Flags: `--task <id>`

1. db.InitDB(dbPath())
2. Call report.Compare(taskID, db.conn) — but report takes *sql.DB not *db.DB
   - Expose db.DB.Conn() *sql.DB method, OR pass db.conn directly
   - Simplest: add `func (d *DB) Conn() *sql.DB { return d.conn }` to db.go
3. Print the result string

## history command

No flags.

1. db.InitDB(dbPath())
2. db.GetRuns("") → all runs
3. Print table: ID | TaskID | Arm | Tokens | Cost | Timestamp

## Shared helpers needed in cli.go

- `dbPath() string` — returns `filepath.Join(os.UserHomeDir(), ".token_miser", "results.db")`
- `DefaultCommander` must actually run subprocesses (fix the panic stubs)

## Acceptance criteria

1. `token-miser run --task tasks/synth-001.yaml --control vanilla --treatment ./ --model sonnet` exits 0 when a fake `claude` binary is on PATH
2. `token-miser compare --task synth-001` prints arm names
3. `token-miser history` prints at least one row after a run
4. All existing tests still pass (`go test ./...`)
5. `go vet ./...` passes

## Notes for the agent

- environment.DefaultCommander currently has `panic("not implemented")` — replace with real os/exec calls
- The Commander.Run method runs a command, the Commander.RunWithOutput method captures stdout
- RunClaude in executor sets HOME and strips CLAUDECODE from env via FilterEnv — do not re-set HOME manually
- Quality scoring is optional: if ANTHROPIC_API_KEY is unset, skip it silently
- Do NOT import the evaluator package if the API key is empty — just skip the call
- The db.Run.QualityScores field is a JSON string (already marshaled), store "{}" if no scores
- tasksCommand is already implemented correctly — do not touch it
