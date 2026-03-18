package cli_test

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/cli"
	"github.com/rubin-johnson/token_miser/internal/db"
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
