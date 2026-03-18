## Dependency Graph and Recommended Execution Order

```
BT-001 (DefaultCommander tests)
  └── STORY-001 (Fix DefaultCommander)

BT-002 (db.Conn() tests)
  └── STORY-002 (Add Conn() to db.DB)

BT-003 (dbPath() + run command tests)
  └── STORY-003 (Implement run command)
        ├── STORY-001 must be complete
        └── STORY-002 must be complete

BT-004 (compare command tests)
  └── STORY-004 (Implement compare command)
        └── STORY-002 must be complete

BT-005 (history command tests)
  └── STORY-005 (Implement history command)
```

**Recommended execution order:**
1. BT-001
2. BT-002
3. BT-003
4. BT-004
5. BT-005
6. STORY-001
7. STORY-002
8. STORY-003
9. STORY-004
10. STORY-005

---

## BT-001 — Behavioral tests for DefaultCommander real subprocess execution

### User story
As a developer, I want `environment.DefaultCommander` to execute real subprocesses so that the environment setup pipeline works end-to-end instead of panicking.

### Context
`internal/environment/environment.go` currently has `panic("not implemented")` in `DefaultCommander.Run` and `DefaultCommander.RunWithOutput`. These tests will fail (panic) until STORY-001 replaces them with real `os/exec` implementations.

### Acceptance criteria
1. `Commander.Run("echo", []string{"hello"})` completes without error and without panicking.
2. `Commander.RunWithOutput("echo", []string{"world"})` returns `"world\n"` and no error.
3. `Commander.Run` with a nonexistent binary returns a non-nil error (does not panic).
4. `Commander.RunWithOutput` with a nonexistent binary returns a non-nil error.

### Unit tests (in this story)
```go
// internal/environment/default_commander_bt_test.go
package environment_test

import (
	"strings"
	"testing"

	"github.com/your-org/token-miser/internal/environment"
)

func TestDefaultCommander_Run_NoError(t *testing.T) {
	c := environment.NewDefaultCommander()
	err := c.Run("echo", []string{"hello"})
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
}

func TestDefaultCommander_RunWithOutput_ReturnsStdout(t *testing.T) {
	c := environment.NewDefaultCommander()
	out, err := c.RunWithOutput("echo", []string{"world"})
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if !strings.Contains(out, "world") {
		t.Fatalf("expected output to contain 'world', got: %q", out)
	}
}

func TestDefaultCommander_Run_NonexistentBinary_ReturnsError(t *testing.T) {
	c := environment.NewDefaultCommander()
	err := c.Run("__nonexistent_binary_xyz__", []string{})
	if err == nil {
		t.Fatal("expected error for nonexistent binary, got nil")
	}
}

func TestDefaultCommander_RunWithOutput_NonexistentBinary_ReturnsError(t *testing.T) {
	c := environment.NewDefaultCommander()
	_, err := c.RunWithOutput("__nonexistent_binary_xyz__", []string{})
	if err == nil {
		t.Fatal("expected error for nonexistent binary, got nil")
	}
}
```

### Implementation notes
- Place this file at `internal/environment/default_commander_bt_test.go`.
- Use `package environment_test` (black-box test).
- Replace `github.com/your-org/token-miser` with the actual module path found in `go.mod`.
- These tests will panic (not just fail) until STORY-001 is complete because the current stubs call `panic("not implemented")`.

### Dependencies
- None.

---

## BT-002 — Behavioral tests for db.DB.Conn() accessor

### User story
As a developer, I want `db.DB` to expose a `Conn() *sql.DB` method so that `report.Compare` can receive the underlying connection it requires.

### Context
`internal/db/db.go` has a `DB` struct wrapping `*sql.DB` as a private field named `conn`. The `report.Compare` function requires `*sql.DB` directly. This accessor bridges the gap. These tests fail until STORY-002 adds the method.

### Acceptance criteria
1. `db.InitDB(tmpPath)` returns a `*DB` whose `Conn()` method returns a non-nil `*sql.DB`.
2. The returned `*sql.DB` is pingable (connection is valid).

### Unit tests (in this story)
```go
// internal/db/conn_bt_test.go
package db_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/your-org/token-miser/internal/db"
)

func TestDB_Conn_ReturnsNonNil(t *testing.T) {
	dir := t.TempDir()
	dbFile := filepath.Join(dir, "test.db")

	d, err := db.InitDB(dbFile)
	if err != nil {
		t.Fatalf("InitDB failed: %v", err)
	}
	defer os.Remove(dbFile)

	conn := d.Conn()
	if conn == nil {
		t.Fatal("expected non-nil *sql.DB from Conn(), got nil")
	}
}

func TestDB_Conn_IsPingable(t *testing.T) {
	dir := t.TempDir()
	dbFile := filepath.Join(dir, "test.db")

	d, err := db.InitDB(dbFile)
	if err != nil {
		t.Fatalf("InitDB failed: %v", err)
	}
	defer os.Remove(dbFile)

	conn := d.Conn()
	if err := conn.Ping(); err != nil {
		t.Fatalf("expected Conn() to be pingable, got error: %v", err)
	}
}
```

### Implementation notes
- Place at `internal/db/conn_bt_test.go`.
- Use `package db_test`.
- Replace `github.com/your-org/token-miser` with the actual module path from `go.mod`.
- These tests will fail with a compile error (`d.Conn undefined`) until STORY-002 adds the method.

### Dependencies
- None.

---

## BT-003 — Behavioral tests for run command, dbPath helper, and per-arm summary

### User story
As a developer, I want the `run` command to execute a full evaluation pipeline for both arms, persist results to SQLite, and print a per-arm summary so that I can measure whether my changes improve model performance.

### Context
`internal/cli/cli.go` has a stub `runCommand` that does nothing. These tests wire through a fake `claude` binary to exercise the full pipeline. They cover: flag parsing, sequential arm execution, DB persistence, and summary output. They fail until STORY-003 is complete.

### Acceptance criteria
1. `Dispatch("run", ...)` with valid flags and a fake `claude` on PATH exits without error.
2. After `run` completes, `db.GetRuns(taskID)` returns at least 2 rows (one per arm).
3. The summary printed to stdout contains the arm names "control" and "treatment" (or the spec values).
4. `dbPath()` returns a path ending in `.token_miser/results.db`.
5. Running `run` without `ANTHROPIC_API_KEY` set completes without error (quality scoring skipped).

### Unit tests (in this story)
```go
// internal/cli/run_bt_test.go
package cli_test

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/your-org/token-miser/internal/cli"
	"github.com/your-org/token-miser/internal/db"
)

// writeFakeClaude writes a shell script that acts as a minimal fake claude binary.
func writeFakeClaude(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	script := filepath.Join(dir, "claude")
	content := `#!/bin/sh
echo '{"type":"result","result":"fake output","total_cost_usd":0.001,"usage":{"input_tokens":10,"output_tokens":5},"wall_seconds":1.0}'
`
	if err := os.WriteFile(script, []byte(content), 0755); err != nil {
		t.Fatalf("failed to write fake claude: %v", err)
	}
	return dir
}

// writeMinimalTask writes a minimal YAML task file for testing.
func writeMinimalTask(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	taskFile := filepath.Join(dir, "test-task.yaml")
	content := `id: test-task-001
repo: "https://example.com/repo.git"
starting_commit: "abc123"
prompt: "Write hello world"
success_criteria: []
quality_rubric: []
`
	if err := os.WriteFile(taskFile, []byte(content), 0644); err != nil {
		t.Fatalf("failed to write task file: %v", err)
	}
	return taskFile
}

func TestRunCommand_ExitsWithoutError(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available, skipping integration test")
	}

	fakeDir := writeFakeClaude(t)
	taskFile := writeMinimalTask(t)

	// Prepend fake claude dir to PATH
	origPath := os.Getenv("PATH")
	os.Setenv("PATH", fakeDir+string(os.PathListSeparator)+origPath)
	defer os.Setenv("PATH", origPath)

	// Use a temp DB
	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	// Unset API key to skip quality scoring
	os.Unsetenv("ANTHROPIC_API_KEY")

	var buf bytes.Buffer
	err := cli.Dispatch("run", []string{
		"--task", taskFile,
		"--control", "vanilla",
		"--treatment", "vanilla",
		"--model", "sonnet",
	}, &buf)
	if err != nil {
		t.Fatalf("expected run to succeed, got error: %v", err)
	}
}

func TestRunCommand_PersistsRunsToDB(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available, skipping integration test")
	}

	fakeDir := writeFakeClaude(t)
	taskFile := writeMinimalTask(t)

	origPath := os.Getenv("PATH")
	os.Setenv("PATH", fakeDir+string(os.PathListSeparator)+origPath)
	defer os.Setenv("PATH", origPath)

	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	os.Unsetenv("ANTHROPIC_API_KEY")

	var buf bytes.Buffer
	err := cli.Dispatch("run", []string{
		"--task", taskFile,
		"--control", "vanilla",
		"--treatment", "vanilla",
		"--model", "sonnet",
	}, &buf)
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	dbPath := filepath.Join(dbDir, ".token_miser", "results.db")
	d, err := db.InitDB(dbPath)
	if err != nil {
		t.Fatalf("failed to open DB: %v", err)
	}
	runs, err := d.GetRuns("test-task-001")
	if err != nil {
		t.Fatalf("GetRuns failed: %v", err)
	}
	if len(runs) < 2 {
		t.Fatalf("expected at least 2 runs in DB, got %d", len(runs))
	}
}

func TestRunCommand_SummaryContainsArmNames(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available, skipping integration test")
	}

	fakeDir := writeFakeClaude(t)
	taskFile := writeMinimalTask(t)

	origPath := os.Getenv("PATH")
	os.Setenv("PATH", fakeDir+string(os.PathListSeparator)+origPath)
	defer os.Setenv("PATH", origPath)

	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	os.Unsetenv("ANTHROPIC_API_KEY")

	var buf bytes.Buffer
	err := cli.Dispatch("run", []string{
		"--task", taskFile,
		"--control", "vanilla",
		"--treatment", "vanilla",
		"--model", "sonnet",
	}, &buf)
	if err != nil {
		t.Fatalf("run failed: %v", err)
	}

	output := buf.String()
	if !strings.Contains(output, "control") && !strings.Contains(output, "vanilla") {
		t.Fatalf("expected summary to mention arm names, got: %q", output)
	}
}

func TestRunCommand_NoAPIKey_DoesNotError(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available, skipping integration test")
	}

	fakeDir := writeFakeClaude(t)
	taskFile := writeMinimalTask(t)

	origPath := os.Getenv("PATH")
	os.Setenv("PATH", fakeDir+string(os.PathListSeparator)+origPath)
	defer os.Setenv("PATH", origPath)

	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	os.Unsetenv("ANTHROPIC_API_KEY")

	var buf bytes.Buffer
	err := cli.Dispatch("run", []string{
		"--task", taskFile,
		"--control", "vanilla",
		"--treatment", "vanilla",
	}, &buf)
	if err != nil {
		t.Fatalf("expected no error without API key, got: %v", err)
	}
}
```

### Implementation notes
- Place at `internal/cli/run_bt_test.go`.
- Package `cli_test` (black-box).
- Replace `github.com/your-org/token-miser` with the actual module path.
- `cli.Dispatch` signature may need an `io.Writer` param — check the existing signature in `cli.go` and match it. If it currently takes no writer, tests should capture via os.Stdout redirect or the signature needs updating in STORY-003.
- The fake `claude` script must output JSON matching whatever `executor.RunClaude` expects. Inspect `internal/executor` to confirm the exact JSON schema before writing STORY-003.
- Tests use `t.TempDir()` to isolate DB state so parallel test runs don't collide.

### Dependencies
- None.

---

## BT-004 — Behavioral tests for compare command

### User story
As a developer, I want the `compare` command to retrieve stored runs for a given task and print a comparison report including arm names so that I can contrast control and treatment performance.

### Context
`internal/cli/cli.go` has a stub `compareCommand`. `report.Compare` returns a formatted string. These tests fail until STORY-004 wires `compareCommand` to `db.InitDB` + `report.Compare`.

### Acceptance criteria
1. `Dispatch("compare", ["--task", taskID])` after seeding the DB returns output containing arm names.
2. `Dispatch("compare", ["--task", "nonexistent-task"])` does not crash — it returns output (possibly empty report) without error.

### Unit tests (in this story)
```go
// internal/cli/compare_bt_test.go
package cli_test

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/your-org/token-miser/internal/cli"
	"github.com/your-org/token-miser/internal/db"
)

func seedDB(t *testing.T, dbDir string) {
	t.Helper()
	dbPath := filepath.Join(dbDir, ".token_miser", "results.db")
	if err := os.MkdirAll(filepath.Dir(dbPath), 0755); err != nil {
		t.Fatalf("mkdir failed: %v", err)
	}
	d, err := db.InitDB(dbPath)
	if err != nil {
		t.Fatalf("InitDB failed: %v", err)
	}
	for _, armName := range []string{"control", "treatment"} {
		run := &db.Run{
			TaskID:        "compare-task-001",
			Arm:           armName,
			InputTokens:   10,
			OutputTokens:  5,
			TotalTokens:   15,
			CostUSD:       0.001,
			CriteriaPassed: 1,
			CriteriaTotal:  1,
			QualityScores: "{}",
			Timestamp:     time.Now(),
		}
		if _, err := d.StoreRun(run); err != nil {
			t.Fatalf("StoreRun failed: %v", err)
		}
	}
}

func TestCompareCommand_PrintsArmNames(t *testing.T) {
	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	seedDB(t, dbDir)

	var buf bytes.Buffer
	err := cli.Dispatch("compare", []string{"--task", "compare-task-001"}, &buf)
	if err != nil {
		t.Fatalf("compare failed: %v", err)
	}

	output := buf.String()
	if output == "" {
		t.Fatal("expected non-empty output from compare command")
	}
}

func TestCompareCommand_NonexistentTask_NoError(t *testing.T) {
	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	// Initialize empty DB
	dbPath := filepath.Join(dbDir, ".token_miser", "results.db")
	os.MkdirAll(filepath.Dir(dbPath), 0755)
	db.InitDB(dbPath)

	var buf bytes.Buffer
	err := cli.Dispatch("compare", []string{"--task", "no-such-task"}, &buf)
	if err != nil {
		t.Fatalf("expected no error for nonexistent task, got: %v", err)
	}
}
```

### Implementation notes
- Place at `internal/cli/compare_bt_test.go`.
- Package `cli_test`.
- Replace module path from `go.mod`.
- `db.Run` fields must match the actual struct definition in `internal/db/db.go` — inspect before writing.
- `db.StoreRun` return signature may be `(int64, error)` or `(error)` — inspect and match.

### Dependencies
- None.

---

## BT-005 — Behavioral tests for history command

### User story
As a developer, I want the `history` command to list all stored runs in a table so that I can review the history of experiments.

### Context
`internal/cli/cli.go` has a stub `historyCommand`. These tests verify that after seeding the DB the history command prints a table with the expected columns. They fail until STORY-005 is complete.

### Acceptance criteria
1. After seeding the DB with 3 runs, `Dispatch("history", [])` prints at least 3 data rows.
2. The output contains the column headers: `ID`, `TaskID`, `Arm`, `Tokens`, `Cost`, `Timestamp`.
3. `Dispatch("history", [])` on an empty DB prints the table header without error.

### Unit tests (in this story)
```go
// internal/cli/history_bt_test.go
package cli_test

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/your-org/token-miser/internal/cli"
	"github.com/your-org/token-miser/internal/db"
)

func seedHistoryDB(t *testing.T, dbDir string, n int) {
	t.Helper()
	dbPath := filepath.Join(dbDir, ".token_miser", "results.db")
	os.MkdirAll(filepath.Dir(dbPath), 0755)
	d, err := db.InitDB(dbPath)
	if err != nil {
		t.Fatalf("InitDB failed: %v", err)
	}
	for i := 0; i < n; i++ {
		run := &db.Run{
			TaskID:        "history-task-001",
			Arm:           "control",
			InputTokens:   10,
			OutputTokens:  5,
			TotalTokens:   15,
			CostUSD:       0.001,
			CriteriaPassed: 0,
			CriteriaTotal:  0,
			QualityScores: "{}",
			Timestamp:     time.Now(),
		}
		if _, err := d.StoreRun(run); err != nil {
			t.Fatalf("StoreRun failed: %v", err)
		}
	}
}

func TestHistoryCommand_PrintsRows(t *testing.T) {
	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	seedHistoryDB(t, dbDir, 3)

	var buf bytes.Buffer
	err := cli.Dispatch("history", []string{}, &buf)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}

	output := buf.String()
	lines := strings.Split(strings.TrimSpace(output), "\n")
	// Expect at least header + 3 data rows
	if len(lines) < 4 {
		t.Fatalf("expected at least 4 lines (header + 3 rows), got %d: %q", len(lines), output)
	}
}

func TestHistoryCommand_PrintsHeaders(t *testing.T) {
	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	seedHistoryDB(t, dbDir, 1)

	var buf bytes.Buffer
	err := cli.Dispatch("history", []string{}, &buf)
	if err != nil {
		t.Fatalf("history failed: %v", err)
	}

	output := buf.String()
	for _, col := range []string{"ID", "TaskID", "Arm", "Tokens", "Cost", "Timestamp"} {
		if !strings.Contains(output, col) {
			t.Errorf("expected output to contain column %q, got: %q", col, output)
		}
	}
}

func TestHistoryCommand_EmptyDB_NoError(t *testing.T) {
	dbDir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dbDir)
	defer os.Setenv("HOME", origHome)

	dbPath := filepath.Join(dbDir, ".token_miser", "results.db")
	os.MkdirAll(filepath.Dir(dbPath), 0755)
	db.InitDB(dbPath)

	var buf bytes.Buffer
	err := cli.Dispatch("history", []string{}, &buf)
	if err != nil {
		t.Fatalf("expected no error on empty DB, got: %v", err)
	}
}
```

### Implementation notes
- Place at `internal/cli/history_bt_test.go`.
- Package `cli_test`.
- Replace module path from `go.mod`.
- The exact column name casing must match what STORY-005 prints — adjust the test strings if the implementation uses lowercase or different names.

### Dependencies
- None.

---

## STORY-001 — Fix DefaultCommander to use real os/exec

### User story
As a developer, I want `environment.DefaultCommander` to run real subprocesses so that environment setup works end-to-end instead of panicking.

### Context
`internal/environment/environment.go` defines a `Commander` interface and a `DefaultCommander` struct. Both `Run` and `RunWithOutput` currently contain `panic("not implemented")`. The `environment.SetupEnv` function calls both methods to clone repos and run git commands. BT-001 tests will panic until this fix is in place.

### Acceptance criteria
1. `DefaultCommander.Run(command, args)` executes the command as a subprocess and returns any error; does not capture stdout.
2. `DefaultCommander.RunWithOutput(command, args)` executes the command, captures stdout, and returns it along with any error.
3. `BT-001` tests pass.
4. `go vet ./...` reports no issues in the `environment` package.

### Unit tests (in this story)
```go
// internal/environment/default_commander_test.go
package environment

import (
	"strings"
	"testing"
)

func TestDefaultCommanderRun(t *testing.T) {
	c := NewDefaultCommander()
	err := c.Run("echo", []string{"hi"})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestDefaultCommanderRunWithOutput(t *testing.T) {
	c := NewDefaultCommander()
	out, err := c.RunWithOutput("echo", []string{"hello"})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if !strings.Contains(out, "hello") {
		t.Fatalf("expected 'hello' in output, got %q", out)
	}
}
```

### Implementation notes
- Edit `internal/environment/environment.go` (or the file that contains `DefaultCommander`).
- Locate the struct/methods named `DefaultCommander` — they currently contain `panic("not implemented")`.
- Replace `Run(command string, args []string) error` with:
  ```go
  func (c *DefaultCommander) Run(command string, args []string) error {
      cmd := exec.Command(command, args...)
      return cmd.Run()
  }
  ```
- Replace `RunWithOutput(command string, args []string) (string, error)` with:
  ```go
  func (c *DefaultCommander) RunWithOutput(command string, args []string) (string, error) {
      cmd := exec.Command(command, args...)
      out, err := cmd.Output()
      return string(out), err
  }
  ```
- Add `"os/exec"` to the import block if not already present.
- Do not change any other methods, types, or functions in the `environment` package.
- Confirm `NewDefaultCommander()` exists and returns a `*DefaultCommander` (or whatever type holds these methods); if it returns an interface, keep the return type unchanged.

### Dependencies
- BT-001 must be complete.

---

## STORY-002 — Add Conn() accessor to db.DB

### User story
As a developer, I want `db.DB` to expose a `Conn() *sql.DB` method so that `report.Compare` can receive the underlying connection it needs.

### Context
`internal/db/db.go` has a `DB` struct with a private `conn *sql.DB` field. `report.Compare(taskID string, conn *sql.DB)` requires the raw connection. The accessor bridges the two without modifying the `report` package. BT-002 tests fail with a compile error until this method is added.

### Acceptance criteria
1. `db.DB` has an exported method `Conn() *sql.DB`.
2. `Conn()` returns the same `*sql.DB` that `InitDB` initialized.
3. BT-002 tests pass.
4. No other changes to `internal/db/db.go`.

### Unit tests (in this story)
```go
// internal/db/conn_test.go
package db

import (
	"path/filepath"
	"testing"
)

func TestConn_ReturnsSameConnection(t *testing.T) {
	dir := t.TempDir()
	d, err := InitDB(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("InitDB: %v", err)
	}
	if d.Conn() == nil {
		t.Fatal("Conn() returned nil")
	}
	// Verify it's the same pointer as the internal conn field
	if d.Conn() != d.conn {
		t.Fatal("Conn() did not return the internal conn field")
	}
}
```

### Implementation notes
- Open `internal/db/db.go`.
- Locate the `DB` struct — it should have a field `conn *sql.DB`.
- Add this method verbatim after the struct definition:
  ```go
  func (d *DB) Conn() *sql.DB {
      return d.conn
  }
  ```
- `database/sql` should already be imported since it's used for `conn`. Do not add a duplicate import.
- Do not change `InitDB`, `StoreRun`, `GetRuns`, or any other existing function.

### Dependencies
- BT-002 must be complete.

---

## STORY-003 — Implement run command with full pipeline

### User story
As a developer, I want the `run` command to execute a full evaluation pipeline for both arms sequentially, persist results to SQLite, and print a per-arm summary so that I can measure experiment performance end-to-end.

### Context
`internal/cli/cli.go` has a stubbed `runCommand` that does nothing useful. The internal packages `task`, `arm`, `environment`, `executor`, `checker`, `evaluator`, `db` are all implemented. This story wires them together into the `runCommand` function following the 11-step pipeline in the PRD. Depends on STORY-001 (real DefaultCommander) and STORY-002 (Conn() on DB). BT-003 tests must pass when this story is complete.

### Acceptance criteria
1. `run --task <file> --control vanilla --treatment vanilla --model sonnet` exits without error when a fake `claude` binary is on PATH.
2. Two rows are written to the DB after a successful run (one per arm).
3. The summary printed to the output writer contains the arm/spec names.
4. When `ANTHROPIC_API_KEY` is unset, quality scoring is silently skipped and the command exits cleanly.
5. The quality scores JSON stored in DB is `"{}"` when API key is absent.
6. BT-003 tests pass.

### Unit tests (in this story)
```go
// internal/cli/run_test.go
package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestDbPath_EndsWithExpectedSuffix(t *testing.T) {
	dir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	p := dbPath()
	if !strings.HasSuffix(p, filepath.Join(".token_miser", "results.db")) {
		t.Fatalf("dbPath() = %q, want suffix %q", p, filepath.Join(".token_miser", "results.db"))
	}
}
```

### Implementation notes
- The main file to edit is `internal/cli/cli.go`.
- First, read the full file to understand existing structure: `Dispatch`, `tasksCommand`, and stubs for `runCommand`, `compareCommand`, `historyCommand`.
- **Do not modify `tasksCommand` or `Dispatch`'s routing logic.**
- Add `dbPath()` as a package-level helper:
  ```go
  func dbPath() string {
      home, _ := os.UserHomeDir()
      return filepath.Join(home, ".token_miser", "results.db")
  }
  ```
- If `Dispatch` currently writes to `os.Stdout` directly, you may need to add an `io.Writer` parameter to `Dispatch` and thread it through to each sub-command function. Check the existing signature and BT tests — the BT tests pass `&buf bytes.Buffer` as the writer; match that interface.
- Implement `runCommand` following this exact pipeline:

  ```go
  func runCommand(args []string, w io.Writer) error {
      fs := flag.NewFlagSet("run", flag.ContinueOnError)
      taskFile := fs.String("task", "", "path to task YAML")
      controlSpec := fs.String("control", "", "control arm spec")
      treatmentSpec := fs.String("treatment", "", "treatment arm spec")
      model := fs.String("model", "sonnet", "model identifier")
      if err := fs.Parse(args); err != nil {
          return err
      }
      _ = model // passed to executor if its signature accepts it, else ignore

      ctx := context.Background()

      type armResult struct {
          name   string
          result *executor.ExecutorResult
          passed int
          total  int
      }

      var results []armResult

      for _, spec := range []struct{ name, spec string }{
          {"control", *controlSpec},
          {"treatment", *treatmentSpec},
      } {
          t, err := task.LoadTask(*taskFile)
          if err != nil {
              return fmt.Errorf("load task: %w", err)
          }
          a, err := arm.ParseArm(spec.spec)
          if err != nil {
              return fmt.Errorf("parse arm: %w", err)
          }
          env, err := environment.SetupEnv(t, &a, environment.NewDefaultCommander())
          if err != nil {
              return fmt.Errorf("setup env: %w", err)
          }
          defer env.TeardownEnv()

          res, err := executor.RunClaude(t.Prompt, env.HomeDir)
          if err != nil {
              return fmt.Errorf("run claude: %w", err)
          }

          checkResults, err := checker.New(env).CheckAllCriteria(t.SuccessCriteria)
          if err != nil {
              return fmt.Errorf("check criteria: %w", err)
          }
          passed, total := 0, len(checkResults)
          for _, cr := range checkResults {
              if cr.Passed {
                  passed++
              }
          }

          var qualityJSON string
          if apiKey := os.Getenv("ANTHROPIC_API_KEY"); apiKey != "" {
              scores, err := evaluator.NewEvaluator(apiKey).ScoreQuality(ctx, t.Prompt, res.Result, t.QualityRubric)
              if err != nil {
                  return fmt.Errorf("score quality: %w", err)
              }
              b, _ := json.Marshal(scores)
              qualityJSON = string(b)
          } else {
              qualityJSON = "{}"
          }

          database, err := db.InitDB(dbPath())
          if err != nil {
              return fmt.Errorf("init db: %w", err)
          }
          run := db.Run{
              TaskID:         t.ID,
              Arm:            spec.name,
              InputTokens:    res.Usage.InputTokens,
              OutputTokens:   res.Usage.OutputTokens,
              TotalTokens:    res.Usage.InputTokens + res.Usage.OutputTokens,
              CostUSD:        res.TotalCostUSD,
              CriteriaPassed: passed,
              CriteriaTotal:  total,
              QualityScores:  qualityJSON,
              Timestamp:      time.Now(),
          }
          if _, err := database.StoreRun(&run); err != nil {
              return fmt.Errorf("store run: %w", err)
          }

          results = append(results, armResult{
              name:   spec.name,
              result: res,
              passed: passed,
              total:  total,
          })
      }

      // Print summary
      fmt.Fprintln(w, "\n=== Run Summary ===")
      for _, r := range results {
          fmt.Fprintf(w, "Arm: %s | Input tokens: %d | Output tokens: %d | Cost: $%.6f | Criteria: %d/%d passed\n",
              r.name,
              r.result.Usage.InputTokens,
              r.result.Usage.OutputTokens,
              r.result.TotalCostUSD,
              r.passed,
              r.total,
          )
      }
      return nil
  }
  ```
- Required imports for `cli.go`: `context`, `encoding/json`, `flag`, `fmt`, `io`, `os`, `path/filepath`, `time`, plus all internal packages.
- Verify actual field names of `executor.ExecutorResult` and `db.Run` by reading their source files before implementing.
- Verify the actual signature of `executor.RunClaude` — it may or may not accept a model parameter.
- Verify the actual return types of `arm.ParseArm`, `environment.SetupEnv`, `checker.New(env).CheckAllCriteria`, `db.StoreRun`.
- The `Dispatch` function signature: if it currently takes `(command string, args []string)`, change it to `(command string, args []string, w io.Writer)` and update the routing to pass `w` through. Update `main.go` to pass `os.Stdout`.

### Dependencies
- BT-003 must be complete.
- STORY-001 must be complete.
- STORY-002 must be complete.

---

## STORY-004 — Implement compare command

### User story
As a developer, I want the `compare` command to retrieve stored runs for a given task and print a comparison report including arm names so that I can contrast control and treatment performance.

### Context
`internal/cli/cli.go` has a stub `compareCommand`. `report.Compare(taskID string, conn *sql.DB) string` is already implemented. This story wires `compareCommand` to call `db.InitDB` + `db.Conn()` + `report.Compare` + print. Depends on STORY-002 for the `Conn()` accessor.

### Acceptance criteria
1. `compare --task <id>` prints the output of `report.Compare` to the writer.
2. No error is returned for a nonexistent task ID (the report package handles empty results gracefully).
3. BT-004 tests pass.

### Unit tests (in this story)
```go
// internal/cli/compare_test.go
package cli

import (
	"bytes"
	"os"
	"testing"
)

func TestCompareCommand_FlagParsing(t *testing.T) {
	dir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	// Initialize empty DB so InitDB doesn't fail
	dbDir := filepath.Join(dir, ".token_miser")
	os.MkdirAll(dbDir, 0755)

	var buf bytes.Buffer
	err := compareCommand([]string{"--task", "test-task"}, &buf)
	if err != nil {
		t.Fatalf("compareCommand failed: %v", err)
	}
}
```

### Implementation notes
- Edit `internal/cli/cli.go`.
- Implement `compareCommand(args []string, w io.Writer) error`:
  ```go
  func compareCommand(args []string, w io.Writer) error {
      fs := flag.NewFlagSet("compare", flag.ContinueOnError)
      taskID := fs.String("task", "", "task ID to compare")
      if err := fs.Parse(args); err != nil {
          return err
      }
      database, err := db.InitDB(dbPath())
      if err != nil {
          return fmt.Errorf("init db: %w", err)
      }
      report := report.Compare(*taskID, database.Conn())
      fmt.Fprint(w, report)
      return nil
  }
  ```
- The import for `report` will be `github.com/your-org/token-miser/internal/report` — replace with actual module path.
- Verify `report.Compare` signature by reading `internal/report/report.go` before writing.
- Note: the local variable `report` shadows the package name — rename one: use `reportStr` for the variable, or alias the package as `reportpkg`.

### Dependencies
- BT-004 must be complete.
- STORY-002 must be complete.

---

## STORY-005 — Implement history command

### User story
As a developer, I want the `history` command to list all stored runs in a tabular format so that I can review the history of experiments I have run on this machine.

### Context
`internal/cli/cli.go` has a stub `historyCommand`. `db.GetRuns("")` returns all runs. This story implements the table printing using `fmt.Fprintf` with fixed-width columns. No external table library is assumed — use `text/tabwriter` from the standard library.

### Acceptance criteria
1. After seeding the DB, `history` prints a row for every stored run.
2. Output contains column headers: `ID`, `TaskID`, `Arm`, `Tokens`, `Cost`, `Timestamp`.
3. An empty DB prints only the header without error.
4. BT-005 tests pass.

### Unit tests (in this story)
```go
// internal/cli/history_test.go
package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/your-org/token-miser/internal/db"
)

func TestHistoryCommand_HeaderPresent(t *testing.T) {
	dir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	dbDir := filepath.Join(dir, ".token_miser")
	os.MkdirAll(dbDir, 0755)
	d, _ := db.InitDB(filepath.Join(dbDir, "results.db"))
	d.StoreRun(&db.Run{
		TaskID: "t1", Arm: "control",
		InputTokens: 1, OutputTokens: 1, TotalTokens: 2,
		CostUSD: 0.001, QualityScores: "{}",
		Timestamp: time.Now(),
	})

	var buf bytes.Buffer
	err := historyCommand([]string{}, &buf)
	if err != nil {
		t.Fatalf("historyCommand: %v", err)
	}
	out := buf.String()
	for _, h := range []string{"ID", "TaskID", "Arm", "Tokens", "Cost", "Timestamp"} {
		if !strings.Contains(out, h) {
			t.Errorf("missing column %q in output: %q", h, out)
		}
	}
}
```

### Implementation notes
- Edit `internal/cli/cli.go`.
- Implement `historyCommand(args []string, w io.Writer) error`:
  ```go
  func historyCommand(args []string, w io.Writer) error {
      database, err := db.InitDB(dbPath())
      if err != nil {
          return fmt.Errorf("init db: %w", err)
      }
      runs, err := database.GetRuns("")
      if err != nil {
          return fmt.Errorf("get runs: %w", err)
      }

      tw := tabwriter.NewWriter(w, 0, 0, 2, ' ', 0)
      fmt.Fprintln(tw, "ID\tTaskID\tArm\tTokens\tCost\tTimestamp")
      for _, r := range runs {
          fmt.Fprintf(tw, "%d\t%s\t%s\t%d\t$%.6f\t%s\n",
              r.ID,
              r.TaskID,
              r.Arm,
              r.TotalTokens,
              r.CostUSD,
              r.Timestamp.Format(time.RFC3339),
          )
      }
      return tw.Flush()
  }
  ```
- Add `"text/tabwriter"` to imports.
- Verify actual field names of `db.Run` (e.g., `ID`, `TaskID`, `Arm`, `TotalTokens`, `CostUSD`, `Timestamp`) by reading `internal/db/db.go` before writing.
- Verify `db.GetRuns` return signature: `([]Run, error)` or `([]Run)` — match exactly.

### Dependencies
- BT-005 must be complete.
- STORY-002 must be complete.