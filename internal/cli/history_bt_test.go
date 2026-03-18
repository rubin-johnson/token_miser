package cli_test

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/cli"
	"github.com/rubin-johnson/token_miser/internal/db"
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
			TotalCostUSD:  0.001,
			CriteriaPass:  0,
			CriteriaTotal: 0,
			QualityScores: "{}",
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
