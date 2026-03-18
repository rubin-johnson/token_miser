package db

import (
	"encoding/json"
	"testing"
)

func setupTestDB(t *testing.T) *DB {
	t.Helper()
	db, err := InitDB(":memory:")
	if err != nil {
		t.Fatalf("Failed to initialize test database: %v", err)
	}
	return db
}

func TestInitDB(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	query := "PRAGMA table_info(runs)"
	rows, err := db.conn.Query(query)
	if err != nil {
		t.Fatalf("Failed to query table info: %v", err)
	}
	defer rows.Close()

	expectedColumns := map[string]bool{
		"id":                false,
		"task_id":           false,
		"arm":               false,
		"loadout_name":      false,
		"model":             false,
		"started_at":        false,
		"wall_seconds":      false,
		"input_tokens":      false,
		"output_tokens":     false,
		"cache_read_tokens": false,
		"total_cost_usd":    false,
		"criteria_pass":     false,
		"criteria_total":    false,
		"quality_scores":    false,
	}

	for rows.Next() {
		var cid int
		var name, dataType string
		var notNull, pk int
		var defaultValue interface{}
		if err := rows.Scan(&cid, &name, &dataType, &notNull, &defaultValue, &pk); err != nil {
			t.Fatalf("Failed to scan column info: %v", err)
		}
		if _, exists := expectedColumns[name]; exists {
			expectedColumns[name] = true
		}
	}

	for column, found := range expectedColumns {
		if !found {
			t.Errorf("Expected column %s not found in runs table", column)
		}
	}
}

func TestStoreRun(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	run := &Run{
		TaskID:        "test-task",
		Arm:           "test-arm",
		InputTokens:   100,
		OutputTokens:  50,
		TotalCostUSD:  0.001,
		QualityScores: `{"accuracy":0.95,"fluency":0.88}`,
	}

	id, err := db.StoreRun(run)
	if err != nil {
		t.Fatalf("Failed to store run: %v", err)
	}
	if id <= 0 {
		t.Errorf("Expected positive ID, got %d", id)
	}

	runs, err := db.GetRuns("")
	if err != nil {
		t.Fatalf("Failed to get runs: %v", err)
	}
	if len(runs) != 1 {
		t.Fatalf("Expected 1 run, got %d", len(runs))
	}

	got := runs[0]
	if got.ID != id {
		t.Errorf("Expected ID %d, got %d", id, got.ID)
	}
	if got.TaskID != run.TaskID {
		t.Errorf("Expected task_id %s, got %s", run.TaskID, got.TaskID)
	}
	if got.Arm != run.Arm {
		t.Errorf("Expected arm %s, got %s", run.Arm, got.Arm)
	}
	if got.InputTokens != run.InputTokens {
		t.Errorf("Expected input_tokens %d, got %d", run.InputTokens, got.InputTokens)
	}
	if got.OutputTokens != run.OutputTokens {
		t.Errorf("Expected output_tokens %d, got %d", run.OutputTokens, got.OutputTokens)
	}
	if got.TotalCostUSD != run.TotalCostUSD {
		t.Errorf("Expected total_cost_usd %f, got %f", run.TotalCostUSD, got.TotalCostUSD)
	}

	var scores map[string]interface{}
	if err := json.Unmarshal([]byte(got.QualityScores), &scores); err != nil {
		t.Fatalf("Failed to unmarshal quality scores: %v", err)
	}
	if scores["accuracy"] != 0.95 {
		t.Errorf("Expected accuracy 0.95, got %v", scores["accuracy"])
	}
}

func TestGetRunsAll(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	for i, taskID := range []string{"task1", "task2", "task1"} {
		_, err := db.StoreRun(&Run{TaskID: taskID, Arm: "arm", QualityScores: `{}`, TotalCostUSD: float64(i) * 0.001})
		if err != nil {
			t.Fatalf("Failed to store run %d: %v", i, err)
		}
	}

	all, err := db.GetRuns("")
	if err != nil {
		t.Fatalf("Failed to get all runs: %v", err)
	}
	if len(all) != 3 {
		t.Errorf("Expected 3 runs, got %d", len(all))
	}
}

func TestGetRunsFiltered(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	for _, taskID := range []string{"synth-001", "synth-001", "other-task"} {
		if _, err := db.StoreRun(&Run{TaskID: taskID, Arm: "arm", QualityScores: `{}`}); err != nil {
			t.Fatalf("Failed to store run: %v", err)
		}
	}

	filtered, err := db.GetRuns("synth-001")
	if err != nil {
		t.Fatalf("Failed to get filtered runs: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("Expected 2 runs for synth-001, got %d", len(filtered))
	}
	for _, r := range filtered {
		if r.TaskID != "synth-001" {
			t.Errorf("Expected task_id synth-001, got %s", r.TaskID)
		}
	}
}

func TestQualityScoresJSONStorage(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	scores := map[string]interface{}{
		"accuracy": 0.95,
		"fluency":  0.88,
	}
	b, _ := json.Marshal(scores)

	id, err := db.StoreRun(&Run{TaskID: "t", Arm: "a", QualityScores: string(b)})
	if err != nil {
		t.Fatalf("Failed to store run: %v", err)
	}

	runs, err := db.GetRuns("")
	if err != nil {
		t.Fatalf("Failed to get runs: %v", err)
	}
	if len(runs) != 1 {
		t.Fatalf("Expected 1 run, got %d", len(runs))
	}
	if runs[0].ID != id {
		t.Errorf("Expected ID %d, got %d", id, runs[0].ID)
	}

	var got map[string]interface{}
	if err := json.Unmarshal([]byte(runs[0].QualityScores), &got); err != nil {
		t.Fatalf("Failed to unmarshal quality scores: %v", err)
	}
	if got["accuracy"] != 0.95 {
		t.Errorf("Expected accuracy 0.95, got %v", got["accuracy"])
	}
}
