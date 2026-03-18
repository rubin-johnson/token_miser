package db

import (
	"encoding/json"
	"testing"
	"time"
)

// setupTestDB creates an in-memory SQLite database for testing
func setupTestDB(t *testing.T) *DB {
	db, err := InitDB(":memory:")
	if err != nil {
		t.Fatalf("Failed to initialize test database: %v", err)
	}
	return db
}

func TestInitDB(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	// Verify that the runs table was created with all required columns
	query := "PRAGMA table_info(runs)"
	rows, err := db.conn.Query(query)
	if err != nil {
		t.Fatalf("Failed to query table info: %v", err)
	}
	defer rows.Close()

	expectedColumns := map[string]bool{
		"id":             false,
		"task_name":      false,
		"arm_name":       false,
		"prompt_tokens":  false,
		"output_tokens":  false,
		"total_tokens":   false,
		"cost":           false,
		"quality_scores": false,
		"timestamp":      false,
	}

	for rows.Next() {
		var cid int
		var name, dataType string
		var notNull, pk int
		var defaultValue interface{}

		err := rows.Scan(&cid, &name, &dataType, &notNull, &defaultValue, &pk)
		if err != nil {
			t.Fatalf("Failed to scan column info: %v", err)
		}

		if _, exists := expectedColumns[name]; exists {
			expectedColumns[name] = true
		}
	}

	// Check that all expected columns were found
	for column, found := range expectedColumns {
		if !found {
			t.Errorf("Expected column %s not found in runs table", column)
		}
	}
}

func TestStoreRun(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	// Test data
	taskName := "test-task"
	armName := "test-arm"
	promptTokens := 100
	outputTokens := 50
	totalTokens := 150
	cost := 0.001
	qualityScores := map[string]interface{}{
		"accuracy": 0.95,
		"fluency":  0.88,
	}

	// Store the run
	id, err := db.StoreRun(taskName, armName, promptTokens, outputTokens, totalTokens, cost, qualityScores)
	if err != nil {
		t.Fatalf("Failed to store run: %v", err)
	}

	if id <= 0 {
		t.Errorf("Expected positive ID, got %d", id)
	}

	// Verify the run was stored correctly
	runs, err := db.GetRuns("")
	if err != nil {
		t.Fatalf("Failed to get runs: %v", err)
	}

	if len(runs) != 1 {
		t.Fatalf("Expected 1 run, got %d", len(runs))
	}

	run := runs[0]
	if run.ID != id {
		t.Errorf("Expected ID %d, got %d", id, run.ID)
	}
	if run.TaskName != taskName {
		t.Errorf("Expected task name %s, got %s", taskName, run.TaskName)
	}
	if run.ArmName != armName {
		t.Errorf("Expected arm name %s, got %s", armName, run.ArmName)
	}
	if run.PromptTokens != promptTokens {
		t.Errorf("Expected prompt tokens %d, got %d", promptTokens, run.PromptTokens)
	}
	if run.OutputTokens != outputTokens {
		t.Errorf("Expected output tokens %d, got %d", outputTokens, run.OutputTokens)
	}
	if run.TotalTokens != totalTokens {
		t.Errorf("Expected total tokens %d, got %d", totalTokens, run.TotalTokens)
	}
	if run.Cost != cost {
		t.Errorf("Expected cost %f, got %f", cost, run.Cost)
	}

	// Verify quality scores are stored and retrieved as JSON string
	var retrievedScores map[string]interface{}
	err = json.Unmarshal([]byte(run.QualityScores), &retrievedScores)
	if err != nil {
		t.Fatalf("Failed to unmarshal quality scores: %v", err)
	}

	if retrievedScores["accuracy"] != 0.95 {
		t.Errorf("Expected accuracy 0.95, got %v", retrievedScores["accuracy"])
	}
	if retrievedScores["fluency"] != 0.88 {
		t.Errorf("Expected fluency 0.88, got %v", retrievedScores["fluency"])
	}

	// Verify timestamp is recent
	if time.Since(run.Timestamp) > time.Minute {
		t.Errorf("Timestamp seems too old: %v", run.Timestamp)
	}
}

func TestGetRunsAll(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	// Store multiple runs
	qualityScores1 := map[string]interface{}{"score": 0.9}
	qualityScores2 := map[string]interface{}{"score": 0.8}
	qualityScores3 := map[string]interface{}{"score": 0.7}

	_, err := db.StoreRun("task1", "arm1", 100, 50, 150, 0.001, qualityScores1)
	if err != nil {
		t.Fatalf("Failed to store run 1: %v", err)
	}

	_, err = db.StoreRun("task2", "arm2", 200, 100, 300, 0.002, qualityScores2)
	if err != nil {
		t.Fatalf("Failed to store run 2: %v", err)
	}

	_, err = db.StoreRun("task1", "arm3", 150, 75, 225, 0.0015, qualityScores3)
	if err != nil {
		t.Fatalf("Failed to store run 3: %v", err)
	}

	// Test GetRuns("") returns all runs
	allRuns, err := db.GetRuns("")
	if err != nil {
		t.Fatalf("Failed to get all runs: %v", err)
	}

	if len(allRuns) != 3 {
		t.Errorf("Expected 3 runs, got %d", len(allRuns))
	}

	// Verify runs are ordered by timestamp DESC (most recent first)
	for i := 0; i < len(allRuns)-1; i++ {
		if allRuns[i].Timestamp.Before(allRuns[i+1].Timestamp) {
			t.Errorf("Runs are not ordered by timestamp DESC")
			break
		}
	}
}

func TestGetRunsFiltered(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	// Store runs for different tasks
	qualityScores := map[string]interface{}{"score": 0.9}

	_, err := db.StoreRun("synth-001", "arm1", 100, 50, 150, 0.001, qualityScores)
	if err != nil {
		t.Fatalf("Failed to store synth-001 run: %v", err)
	}

	_, err = db.StoreRun("synth-001", "arm2", 200, 100, 300, 0.002, qualityScores)
	if err != nil {
		t.Fatalf("Failed to store synth-001 run: %v", err)
	}

	_, err = db.StoreRun("other-task", "arm1", 150, 75, 225, 0.0015, qualityScores)
	if err != nil {
		t.Fatalf("Failed to store other-task run: %v", err)
	}

	// Test GetRuns("synth-001") returns only runs for that task
	filteredRuns, err := db.GetRuns("synth-001")
	if err != nil {
		t.Fatalf("Failed to get filtered runs: %v", err)
	}

	if len(filteredRuns) != 2 {
		t.Errorf("Expected 2 runs for synth-001, got %d", len(filteredRuns))
	}

	// Verify all returned runs are for the correct task
	for _, run := range filteredRuns {
		if run.TaskName != "synth-001" {
			t.Errorf("Expected task name synth-001, got %s", run.TaskName)
		}
	}
}

func TestQualityScoresJSONStorage(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	// Test complex quality scores structure
	qualityScores := map[string]interface{}{
		"accuracy":    0.95,
		"fluency":     0.88,
		"coherence":   0.92,
		"subcategory": map[string]interface{}{
			"grammar": 0.89,
			"style":   0.91,
		},
		"tags": []string{"good", "coherent"},
	}

	id, err := db.StoreRun("test-task", "test-arm", 100, 50, 150, 0.001, qualityScores)
	if err != nil {
		t.Fatalf("Failed to store run with complex quality scores: %v", err)
	}

	// Retrieve and verify
	runs, err := db.GetRuns("")
	if err != nil {
		t.Fatalf("Failed to get runs: %v", err)
	}

	if len(runs) != 1 {
		t.Fatalf("Expected 1 run, got %d", len(runs))
	}

	run := runs[0]
	if run.ID != id {
		t.Errorf("Expected ID %d, got %d", id, run.ID)
	}

	// Verify quality scores are stored as JSON string and can be unmarshaled
	var retrievedScores map[string]interface{}
	err = json.Unmarshal([]byte(run.QualityScores), &retrievedScores)
	if err != nil {
		t.Fatalf("Failed to unmarshal quality scores: %v", err)
	}

	// Check top-level values
	if retrievedScores["accuracy"] != 0.95 {
		t.Errorf("Expected accuracy 0.95, got %v", retrievedScores["accuracy"])
	}
	if retrievedScores["fluency"] != 0.88 {
		t.Errorf("Expected fluency 0.88, got %v", retrievedScores["fluency"])
	}

	// Check nested structure
	subcategory, ok := retrievedScores["subcategory"].(map[string]interface{})
	if !ok {
		t.Errorf("Expected subcategory to be a map")
	} else {
		if subcategory["grammar"] != 0.89 {
			t.Errorf("Expected grammar 0.89, got %v", subcategory["grammar"])
		}
	}

	// Check array
	tags, ok := retrievedScores["tags"].([]interface{})
	if !ok {
		t.Errorf("Expected tags to be an array")
	} else if len(tags) != 2 {
		t.Errorf("Expected 2 tags, got %d", len(tags))
	}
}
