package checker

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/environment"
	"github.com/rubin-johnson/token_miser/internal/task"
)

func TestChecker_CheckFileExists(t *testing.T) {
	// Create temporary directory for testing
	tempDir := t.TempDir()
	env := &environment.EnvironmentContext{
		WorkspaceDir: tempDir,
		HomeDir:      "/tmp",
	}
	checker := New(env)

	// Create a test file
	testFile := filepath.Join(tempDir, "test.txt")
	if err := os.WriteFile(testFile, []byte("test"), 0644); err != nil {
		t.Fatal(err)
	}

	// Test existing file
	criterion := task.Criterion{
		Type:  "file_exists",
		Paths: []string{"test.txt"},
	}
	result := checker.CheckCriterion(criterion)
	if !result.Passed {
		t.Errorf("Expected file_exists to pass, got: %s", result.Detail)
	}

	// Test missing file
	criterion = task.Criterion{
		Type:  "file_exists",
		Paths: []string{"missing.txt"},
	}
	result = checker.CheckCriterion(criterion)
	if result.Passed {
		t.Error("Expected file_exists to fail for missing file")
	}
	if result.Detail != "missing paths: missing.txt" {
		t.Errorf("Expected detail about missing paths, got: %s", result.Detail)
	}

	// Test multiple files with some missing
	criterion = task.Criterion{
		Type:  "file_exists",
		Paths: []string{"test.txt", "missing1.txt", "missing2.txt"},
	}
	result = checker.CheckCriterion(criterion)
	if result.Passed {
		t.Error("Expected file_exists to fail when some files are missing")
	}
	if result.Detail != "missing paths: missing1.txt, missing2.txt" {
		t.Errorf("Expected detail about missing paths, got: %s", result.Detail)
	}
}

func TestChecker_CheckCommandExitsZero(t *testing.T) {
	tempDir := t.TempDir()
	env := &environment.EnvironmentContext{
		WorkspaceDir: tempDir,
		HomeDir:      tempDir,
	}
	checker := New(env)

	// Test successful command
	criterion := task.Criterion{
		Type:    "command_exits_zero",
		Command: "echo 'hello'",
	}
	result := checker.CheckCriterion(criterion)
	if !result.Passed {
		t.Errorf("Expected command_exits_zero to pass, got: %s", result.Detail)
	}

	// Test failing command
	criterion = task.Criterion{
		Type:    "command_exits_zero",
		Command: "exit 1",
	}
	result = checker.CheckCriterion(criterion)
	if result.Passed {
		t.Error("Expected command_exits_zero to fail for non-zero exit")
	}

	// Test command with stderr output
	criterion = task.Criterion{
		Type:    "command_exits_zero",
		Command: "echo 'error message' >&2 && exit 1",
	}
	result = checker.CheckCriterion(criterion)
	if result.Passed {
		t.Error("Expected command_exits_zero to fail")
	}
	if result.Detail != "error message\n" {
		t.Errorf("Expected stderr in detail, got: %q", result.Detail)
	}
}

func TestChecker_CheckOutputContains(t *testing.T) {
	tempDir := t.TempDir()
	env := &environment.EnvironmentContext{
		WorkspaceDir: tempDir,
		HomeDir:      tempDir,
	}
	checker := New(env)

	// Test output contains all strings
	criterion := task.Criterion{
		Type:           "output_contains",
		Command:        "echo 'hello world test'",
		Contains: []string{"hello", "world"},
	}
	result := checker.CheckCriterion(criterion)
	if !result.Passed {
		t.Errorf("Expected output_contains to pass, got: %s", result.Detail)
	}

	// Test output missing some strings
	criterion = task.Criterion{
		Type:           "output_contains",
		Command:        "echo 'hello world'",
		Contains: []string{"hello", "missing", "also_missing"},
	}
	result = checker.CheckCriterion(criterion)
	if result.Passed {
		t.Error("Expected output_contains to fail when strings are missing")
	}
	if result.Detail != "missing strings in output: missing, also_missing" {
		t.Errorf("Expected detail about missing strings, got: %s", result.Detail)
	}

	// Test command failure
	criterion = task.Criterion{
		Type:           "output_contains",
		Command:        "exit 1",
		Contains: []string{"anything"},
	}
	result = checker.CheckCriterion(criterion)
	if result.Passed {
		t.Error("Expected output_contains to fail when command fails")
	}
}

func TestChecker_CheckAllCriteria(t *testing.T) {
	tempDir := t.TempDir()
	env := &environment.EnvironmentContext{
		WorkspaceDir: tempDir,
		HomeDir:      tempDir,
	}
	checker := New(env)

	// Create a test file
	testFile := filepath.Join(tempDir, "test.txt")
	if err := os.WriteFile(testFile, []byte("test"), 0644); err != nil {
		t.Fatal(err)
	}

	criteria := []task.Criterion{
		{
			Type:      "file_exists",
			Paths: []string{"test.txt"},
		},
		{
			Type:    "command_exits_zero",
			Command: "echo 'success'",
		},
		{
			Type:      "file_exists",
			Paths: []string{"missing.txt"},
		},
	}

	results := checker.CheckAllCriteria(criteria)

	if len(results) != 3 {
		t.Errorf("Expected 3 results, got %d", len(results))
	}

	// First criterion should pass
	if !results[0].Passed {
		t.Error("Expected first criterion to pass")
	}

	// Second criterion should pass
	if !results[1].Passed {
		t.Error("Expected second criterion to pass")
	}

	// Third criterion should fail
	if results[2].Passed {
		t.Error("Expected third criterion to fail")
	}
}

func TestChecker_UnknownCriterionType(t *testing.T) {
	env := &environment.EnvironmentContext{
		WorkspaceDir: "/tmp",
		HomeDir:      "/tmp",
	}
	checker := New(env)

	criterion := task.Criterion{
		Type: "unknown_type",
	}
	result := checker.CheckCriterion(criterion)
	if result.Passed {
		t.Error("Expected unknown criterion type to fail")
	}
	if result.Detail != "unknown criterion type: unknown_type" {
		t.Errorf("Expected error about unknown type, got: %s", result.Detail)
	}
}

func TestChecker_EnvironmentSetup(t *testing.T) {
	tempDir := t.TempDir()
	homeDir := filepath.Join(tempDir, "home")
	if err := os.MkdirAll(homeDir, 0755); err != nil {
		t.Fatal(err)
	}

	env := &environment.EnvironmentContext{
		WorkspaceDir: tempDir,
		HomeDir:      homeDir,
	}
	checker := New(env)

	// Test that HOME is set correctly
	criterion := task.Criterion{
		Type:     "output_contains",
		Command:  "echo $HOME",
		Contains: []string{homeDir},
	}
	result := checker.CheckCriterion(criterion)
	if !result.Passed {
		t.Errorf("Expected HOME to be set correctly, got: %s", result.Detail)
	}
}
