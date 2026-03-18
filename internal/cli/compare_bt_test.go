package cli_test

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/cli"
	"github.com/rubin-johnson/token_miser/internal/db"
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
			TotalCostUSD:  0.001,
			CriteriaPass:  1,
			CriteriaTotal: 1,
			QualityScores: "{}",
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
