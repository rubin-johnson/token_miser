package task

import (
	"strings"
	"testing"
)

func TestLoadTask_Valid(t *testing.T) {
	task, err := LoadTask("testdata/valid.yaml")
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if task == nil {
		t.Fatal("Expected task to be non-nil")
	}

	// Check all fields are populated
	if task.ID != "task-001" {
		t.Errorf("Expected ID 'task-001', got '%s'", task.ID)
	}
	if task.Name != "Test Task" {
		t.Errorf("Expected Name 'Test Task', got '%s'", task.Name)
	}
	if task.Type != "single_shot" {
		t.Errorf("Expected Type 'single_shot', got '%s'", task.Type)
	}
	if task.Repo != "https://github.com/example/repo" {
		t.Errorf("Expected Repo 'https://github.com/example/repo', got '%s'", task.Repo)
	}
	if task.StartingCommit != "abc123" {
		t.Errorf("Expected StartingCommit 'abc123', got '%s'", task.StartingCommit)
	}
	if task.Prompt != "Implement a feature" {
		t.Errorf("Expected Prompt 'Implement a feature', got '%s'", task.Prompt)
	}

	// Check success criteria
	if len(task.SuccessCriteria) != 3 {
		t.Errorf("Expected 3 success criteria, got %d", len(task.SuccessCriteria))
	}

	// Check first criterion
	if len(task.SuccessCriteria) > 0 {
		crit := task.SuccessCriteria[0]
		if crit.Type != "file_exists" {
			t.Errorf("Expected first criterion type 'file_exists', got '%s'", crit.Type)
		}
		if len(crit.Paths) != 2 || crit.Paths[0] != "src/main.go" || crit.Paths[1] != "README.md" {
			t.Errorf("Expected paths [src/main.go, README.md], got %v", crit.Paths)
		}
	}

	// Check second criterion
	if len(task.SuccessCriteria) > 1 {
		crit := task.SuccessCriteria[1]
		if crit.Type != "command_success" {
			t.Errorf("Expected second criterion type 'command_success', got '%s'", crit.Type)
		}
		if crit.Command != "go test ./..." {
			t.Errorf("Expected command 'go test ./...', got '%s'", crit.Command)
		}
	}

	// Check third criterion
	if len(task.SuccessCriteria) > 2 {
		crit := task.SuccessCriteria[2]
		if crit.Type != "output_contains" {
			t.Errorf("Expected third criterion type 'output_contains', got '%s'", crit.Type)
		}
		if len(crit.Contains) != 2 || crit.Contains[0] != "success" || crit.Contains[1] != "passed" {
			t.Errorf("Expected contains [success, passed], got %v", crit.Contains)
		}
	}

	// Check quality rubric
	if len(task.QualityRubric) != 2 {
		t.Errorf("Expected 2 quality rubric dimensions, got %d", len(task.QualityRubric))
	}

	if len(task.QualityRubric) > 0 {
		rubric := task.QualityRubric[0]
		if rubric.Dimension != "code_quality" {
			t.Errorf("Expected first dimension 'code_quality', got '%s'", rubric.Dimension)
		}
		if rubric.Prompt != "Rate the code quality from 1-10" {
			t.Errorf("Expected first prompt 'Rate the code quality from 1-10', got '%s'", rubric.Prompt)
		}
	}

	if len(task.QualityRubric) > 1 {
		rubric := task.QualityRubric[1]
		if rubric.Dimension != "documentation" {
			t.Errorf("Expected second dimension 'documentation', got '%s'", rubric.Dimension)
		}
		if rubric.Prompt != "Evaluate documentation completeness" {
			t.Errorf("Expected second prompt 'Evaluate documentation completeness', got '%s'", rubric.Prompt)
		}
	}
}

func TestLoadTask_MissingID(t *testing.T) {
	_, err := LoadTask("testdata/missing-id.yaml")
	if err == nil {
		t.Fatal("Expected error for missing ID, got nil")
	}

	if !strings.Contains(err.Error(), "id") {
		t.Errorf("Expected error to contain 'id', got: %v", err)
	}
}

func TestLoadTask_NonexistentFile(t *testing.T) {
	_, err := LoadTask("nonexistent.yaml")
	if err == nil {
		t.Fatal("Expected error for nonexistent file, got nil")
	}
}

func TestCriterionStruct(t *testing.T) {
	// Test that Criterion struct has the required typed fields
	crit := Criterion{
		Type:     "test_type",
		Paths:    []string{"path1", "path2"},
		Command:  "test_command",
		Contains: []string{"contains1", "contains2"},
	}

	if crit.Type != "test_type" {
		t.Errorf("Expected Type 'test_type', got '%s'", crit.Type)
	}
	if len(crit.Paths) != 2 {
		t.Errorf("Expected 2 paths, got %d", len(crit.Paths))
	}
	if crit.Command != "test_command" {
		t.Errorf("Expected Command 'test_command', got '%s'", crit.Command)
	}
	if len(crit.Contains) != 2 {
		t.Errorf("Expected 2 contains items, got %d", len(crit.Contains))
	}
}

func TestRubricDimensionStruct(t *testing.T) {
	// Test that RubricDimension struct has the required fields
	rubric := RubricDimension{
		Dimension: "test_dimension",
		Prompt:    "test_prompt",
	}

	if rubric.Dimension != "test_dimension" {
		t.Errorf("Expected Dimension 'test_dimension', got '%s'", rubric.Dimension)
	}
	if rubric.Prompt != "test_prompt" {
		t.Errorf("Expected Prompt 'test_prompt', got '%s'", rubric.Prompt)
	}
}
