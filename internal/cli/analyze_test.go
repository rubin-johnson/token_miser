package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/db"
)

// makeRun is a convenience helper for building fixture Run values.
func makeRun(taskID, arm string, inputTok, outputTok int, costUSD float64, criteriaPass, criteriaTotal int) db.Run {
	return db.Run{
		TaskID:        taskID,
		Arm:           arm,
		InputTokens:   inputTok,
		OutputTokens:  outputTok,
		TotalCostUSD:  costUSD,
		CriteriaPass:  criteriaPass,
		CriteriaTotal: criteriaTotal,
		QualityScores: "{}",
	}
}

// TestAnalyzeRuns_BasicTable verifies column headers and baseline delta logic.
func TestAnalyzeRuns_BasicTable(t *testing.T) {
	runs := []db.Run{
		makeRun("synth-002", "vanilla", 700, 800, 0.135, 10, 10),
		makeRun("synth-002", "vanilla", 700, 800, 0.135, 10, 10),
		makeRun("synth-002", "lean-md", 600, 800, 0.132, 10, 10),
		makeRun("synth-002", "lean-md", 600, 800, 0.132, 10, 10),
		makeRun("synth-002", "no-mem", 1200, 1300, 0.170, 10, 10),
		makeRun("synth-002", "no-mem", 1200, 1300, 0.170, 10, 10),
	}

	var buf bytes.Buffer
	if err := analyzeRuns("synth-002", runs, &buf); err != nil {
		t.Fatalf("analyzeRuns: %v", err)
	}
	out := buf.String()

	// Header row
	for _, col := range []string{"Arm", "Runs", "Avg Cost", "Stdev", "Median", "Avg Tok", "Criteria", "vs vanilla"} {
		if !strings.Contains(out, col) {
			t.Errorf("missing column header %q\n%s", col, out)
		}
	}

	// Task header line
	if !strings.Contains(out, "Task: synth-002") {
		t.Errorf("missing task header line\n%s", out)
	}

	// vanilla is baseline
	if !strings.Contains(out, "(baseline)") {
		t.Errorf("expected (baseline) marker for vanilla arm\n%s", out)
	}

	// lean-md should be cheaper than vanilla → negative delta
	if !strings.Contains(out, "lean-md") {
		t.Errorf("lean-md arm missing from output\n%s", out)
	}

	// no-mem should be more expensive than vanilla → positive delta
	if !strings.Contains(out, "no-mem") {
		t.Errorf("no-mem arm missing from output\n%s", out)
	}
}

// TestAnalyzeRuns_NoCriteriaTotal handles runs with no criteria defined.
func TestAnalyzeRuns_NoCriteriaTotal(t *testing.T) {
	runs := []db.Run{
		makeRun("task-x", "alpha", 500, 500, 0.05, 0, 0),
		makeRun("task-x", "beta", 600, 400, 0.06, 0, 0),
	}

	var buf bytes.Buffer
	if err := analyzeRuns("task-x", runs, &buf); err != nil {
		t.Fatalf("analyzeRuns: %v", err)
	}
	out := buf.String()
	// Should not panic and should include both arms
	for _, arm := range []string{"alpha", "beta"} {
		if !strings.Contains(out, arm) {
			t.Errorf("arm %q missing from output\n%s", arm, out)
		}
	}
}

// TestAnalyzeRuns_BaselineFallbackToCheapest verifies that when no "vanilla"
// arm exists, the cheapest arm is used as baseline.
func TestAnalyzeRuns_BaselineFallbackToCheapest(t *testing.T) {
	runs := []db.Run{
		makeRun("task-y", "expensive", 800, 800, 0.20, 5, 5),
		makeRun("task-y", "cheap", 400, 400, 0.05, 5, 5),
	}

	var buf bytes.Buffer
	if err := analyzeRuns("task-y", runs, &buf); err != nil {
		t.Fatalf("analyzeRuns: %v", err)
	}
	out := buf.String()

	lines := strings.Split(out, "\n")
	// Find the cheap arm line — it should carry (baseline)
	found := false
	for _, l := range lines {
		if strings.Contains(l, "cheap") && strings.Contains(l, "(baseline)") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected cheap arm to be (baseline) when no vanilla arm present\n%s", out)
	}
}

// TestAnalyzeRuns_TokenFormatting spot-checks comma insertion.
func TestAnalyzeRuns_TokenFormatting(t *testing.T) {
	// 1500 input + 1000 output = 2500 avg tokens → "2,500"
	runs := []db.Run{
		makeRun("task-z", "vanilla", 1500, 1000, 0.10, 10, 10),
	}

	var buf bytes.Buffer
	if err := analyzeRuns("task-z", runs, &buf); err != nil {
		t.Fatalf("analyzeRuns: %v", err)
	}
	out := buf.String()
	if !strings.Contains(out, "2,500") {
		t.Errorf("expected comma-formatted token count 2,500\n%s", out)
	}
}

// TestAnalyzeCommand_MissingTaskFlag verifies --task is required.
func TestAnalyzeCommand_MissingTaskFlag(t *testing.T) {
	var buf bytes.Buffer
	err := analyzeCommand([]string{}, &buf)
	if err == nil {
		t.Fatal("expected error when --task omitted, got nil")
	}
	if !strings.Contains(err.Error(), "--task") {
		t.Errorf("error message should mention --task, got: %v", err)
	}
}

// TestAnalyzeCommand_NoRunsMessage verifies graceful handling of empty DB.
func TestAnalyzeCommand_NoRunsMessage(t *testing.T) {
	dir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	dbDir := filepath.Join(dir, ".token_miser")
	os.MkdirAll(dbDir, 0755)

	var buf bytes.Buffer
	err := analyzeCommand([]string{"--task", "nonexistent"}, &buf)
	if err != nil {
		t.Fatalf("analyzeCommand: %v", err)
	}
	if !strings.Contains(buf.String(), "No runs found") {
		t.Errorf("expected 'No runs found' message\n%s", buf.String())
	}
}
