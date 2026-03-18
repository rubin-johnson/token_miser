package report

import (
	"database/sql"
	"strings"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/db"
)

func TestCompare_NoRuns(t *testing.T) {
	// Create in-memory database
	database, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open database: %v", err)
	}
	defer database.Close()

	// Initialize schema
	if _, err := database.Exec(`CREATE TABLE runs (
		id INTEGER PRIMARY KEY,
		task_id TEXT,
		arm TEXT,
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
	)`); err != nil {
		t.Fatalf("Failed to create schema: %v", err)
	}

	result, err := Compare("nonexistent", database)
	if err != nil {
		t.Fatalf("Compare failed: %v", err)
	}

	if !strings.Contains(result, "No runs found") {
		t.Errorf("Expected 'No runs found' message, got: %s", result)
	}
}

func TestCompare_SingleArm(t *testing.T) {
	// Create fixture runs
	runs := []*db.Run{
		{
			TaskID:        "task1",
			Arm:           "control",
			InputTokens:   100,
			OutputTokens:  50,
			TotalCostUSD:  0.001,
			WallSeconds:   1.5,
			CriteriaPass:  2,
			CriteriaTotal: 3,
			QualityScores: `{"accuracy": 0.85, "fluency": 0.92}`,
		},
		{
			TaskID:        "task1",
			Arm:           "control",
			InputTokens:   120,
			OutputTokens:  60,
			TotalCostUSD:  0.002,
			WallSeconds:   2.0,
			CriteriaPass:  3,
			CriteriaTotal: 3,
			QualityScores: `{"accuracy": 0.90, "fluency": 0.88}`,
		},
	}

	database := setupTestDB(t, runs)
	defer database.Close()

	result, err := Compare("task1", database)
	if err != nil {
		t.Fatalf("Compare failed: %v", err)
	}

	// Check key strings appear in output
	expectedStrings := []string{
		"Comparison for task: task1",
		"Arm: control",
		"Total tokens:",
		"Cost:",
		"Wall time:",
		"Criteria pass rate:",
		"accuracy:",
		"fluency:",
	}

	for _, expected := range expectedStrings {
		if !strings.Contains(result, expected) {
			t.Errorf("Expected output to contain %q, got: %s", expected, result)
		}
	}
}

func TestCompare_TwoArms_SideBySide(t *testing.T) {
	// Create fixture runs with exactly two arms
	runs := []*db.Run{
		{
			TaskID:        "task2",
			Arm:           "control",
			InputTokens:   100,
			OutputTokens:  50,
			TotalCostUSD:  0.001,
			WallSeconds:   1.5,
			CriteriaPass:  2,
			CriteriaTotal: 3,
			QualityScores: `{"accuracy": 0.85}`,
		},
		{
			TaskID:        "task2",
			Arm:           "treatment",
			InputTokens:   110,
			OutputTokens:  55,
			TotalCostUSD:  0.0015,
			WallSeconds:   1.8,
			CriteriaPass:  3,
			CriteriaTotal: 3,
			QualityScores: `{"accuracy": 0.90}`,
		},
	}

	database := setupTestDB(t, runs)
	defer database.Close()

	result, err := Compare("task2", database)
	if err != nil {
		t.Fatalf("Compare failed: %v", err)
	}

	// Check for side-by-side format indicators
	expectedStrings := []string{
		"Comparison for task: task2",
		"control",
		"treatment",
		"|", // Side-by-side separator
		"Total tokens:",
		"Cost:",
		"Wall time:",
		"Criteria:",
		"accuracy:",
	}

	for _, expected := range expectedStrings {
		if !strings.Contains(result, expected) {
			t.Errorf("Expected output to contain %q, got: %s", expected, result)
		}
	}

	// Verify it's actually side-by-side (contains pipe separator)
	lines := strings.Split(result, "\n")
	hasPipeSeparator := false
	for _, line := range lines {
		if strings.Contains(line, "|") && strings.Contains(line, "Total tokens:") {
			hasPipeSeparator = true
			break
		}
	}
	if !hasPipeSeparator {
		t.Error("Expected side-by-side format with pipe separator")
	}
}

func TestCompare_ThreeArms_Stacked(t *testing.T) {
	// Create fixture runs with three arms
	runs := []*db.Run{
		{
			TaskID:        "task3",
			Arm:           "control",
			InputTokens:   100,
			OutputTokens:  50,
			TotalCostUSD:  0.001,
			WallSeconds:   1.5,
			CriteriaPass:  2,
			CriteriaTotal: 3,
			QualityScores: `{"accuracy": 0.85}`,
		},
		{
			TaskID:        "task3",
			Arm:           "treatment1",
			InputTokens:   110,
			OutputTokens:  55,
			TotalCostUSD:  0.0015,
			WallSeconds:   1.8,
			CriteriaPass:  3,
			CriteriaTotal: 3,
			QualityScores: `{"accuracy": 0.90}`,
		},
		{
			TaskID:        "task3",
			Arm:           "treatment2",
			InputTokens:   95,
			OutputTokens:  45,
			TotalCostUSD:  0.0008,
			WallSeconds:   1.2,
			CriteriaPass:  1,
			CriteriaTotal: 3,
			QualityScores: `{"accuracy": 0.80}`,
		},
	}

	database := setupTestDB(t, runs)
	defer database.Close()

	result, err := Compare("task3", database)
	if err != nil {
		t.Fatalf("Compare failed: %v", err)
	}

	// Check for stacked format
	expectedStrings := []string{
		"Comparison for task: task3",
		"Arm: control",
		"Arm: treatment1",
		"Arm: treatment2",
		"Total tokens:",
		"Cost:",
		"Wall time:",
		"Criteria pass rate:",
		"accuracy:",
	}

	for _, expected := range expectedStrings {
		if !strings.Contains(result, expected) {
			t.Errorf("Expected output to contain %q, got: %s", expected, result)
		}
	}

	// Should NOT contain pipe separator (not side-by-side)
	if strings.Contains(result, "|") {
		t.Error("Expected stacked format, but found pipe separator")
	}
}

func setupTestDB(t *testing.T, runs []*db.Run) *sql.DB {
	database, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open database: %v", err)
	}

	// Initialize schema
	if _, err := database.Exec(`CREATE TABLE runs (
		id INTEGER PRIMARY KEY,
		task_id TEXT,
		arm TEXT,
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
	)`); err != nil {
		t.Fatalf("Failed to create schema: %v", err)
	}

	// Insert test data
	for _, run := range runs {
		_, err := database.Exec(`INSERT INTO runs
			(task_id, arm, loadout_name, model, started_at, wall_seconds,
			 input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
			 total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
			run.TaskID, run.Arm, run.LoadoutName, run.Model, run.StartedAt,
			run.WallSeconds, run.InputTokens, run.OutputTokens,
			run.CacheReadTokens, run.CacheWriteTokens, run.TotalCostUSD,
			run.ExitCode, run.CriteriaPass, run.CriteriaTotal, run.QualityScores)
		if err != nil {
			t.Fatalf("Failed to insert test data: %v", err)
		}
	}

	return database
}
