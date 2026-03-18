package cmd

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// TestEndToEndSmokeTest validates the full pipeline with a fake Claude binary
func TestEndToEndSmokeTest(t *testing.T) {
	// Create temporary directory for fake claude binary
	tempDir, err := ioutil.TempDir("", "token-miser-smoke-test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create fake claude script
	fakeClaude := filepath.Join(tempDir, "claude")
	claudeScript := `#!/bin/bash
# Fake Claude binary for smoke testing
cat << 'EOF'
{
  "result": "This is a fake Claude response for testing purposes.",
  "total_cost_usd": 0.001234,
  "usage": {
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150
  }
}
EOF
`

	err = ioutil.WriteFile(fakeClaude, []byte(claudeScript), 0755)
	if err != nil {
		t.Fatalf("Failed to create fake claude script: %v", err)
	}

	// Add temp dir to PATH for this test
	originalPath := os.Getenv("PATH")
	newPath := tempDir + string(os.PathListSeparator) + originalPath
	os.Setenv("PATH", newPath)
	defer os.Setenv("PATH", originalPath)

	// Verify fake claude works
	cmd := exec.Command("claude")
	output, err := cmd.Output()
	if err != nil {
		t.Fatalf("Fake claude script failed: %v", err)
	}

	// Validate JSON structure
	var claudeResponse struct {
		Result      string  `json:"result"`
		TotalCostUSD float64 `json:"total_cost_usd"`
		Usage       struct {
			InputTokens  int `json:"input_tokens"`
			OutputTokens int `json:"output_tokens"`
			TotalTokens  int `json:"total_tokens"`
		} `json:"usage"`
	}

	err = json.Unmarshal(output, &claudeResponse)
	if err != nil {
		t.Fatalf("Fake claude output is not valid JSON: %v", err)
	}

	if claudeResponse.Result == "" {
		t.Fatal("Fake claude response missing 'result' field")
	}
	if claudeResponse.TotalCostUSD == 0 {
		t.Fatal("Fake claude response missing 'total_cost_usd' field")
	}
	if claudeResponse.Usage.TotalTokens == 0 {
		t.Fatal("Fake claude response missing 'usage' field")
	}

	// Create a temporary working directory for the test
	workDir, err := ioutil.TempDir("", "token-miser-work")
	if err != nil {
		t.Fatalf("Failed to create work dir: %v", err)
	}
	defer os.RemoveAll(workDir)

	// Change to work directory
	originalWd, _ := os.Getwd()
	os.Chdir(workDir)
	defer os.Chdir(originalWd)

	// Copy tasks directory to work directory
	tasksDir := filepath.Join(workDir, "tasks")
	err = os.MkdirAll(tasksDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create tasks dir: %v", err)
	}

	// Create synth-001.yaml task file
	taskContent := `name: synth-001
description: Synthetic test task
prompt: "Generate a simple hello world program"
expected_output: "Hello, World!"
`
	taskFile := filepath.Join(tasksDir, "synth-001.yaml")
	err = ioutil.WriteFile(taskFile, []byte(taskContent), 0644)
	if err != nil {
		t.Fatalf("Failed to create task file: %v", err)
	}

	// Create treatment directory
	treatmentDir := filepath.Join(workDir, "treatment")
	err = os.MkdirAll(treatmentDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create treatment dir: %v", err)
	}

	// Run token-miser run command
	binaryPath := filepath.Join(originalWd, "token-miser")
	if _, err := os.Stat(binaryPath); os.IsNotExist(err) {
		// Try to build the binary first
		buildCmd := exec.Command("go", "build", "-o", "token-miser", ".")
		buildCmd.Dir = originalWd
		err = buildCmd.Run()
		if err != nil {
			t.Fatalf("Failed to build token-miser binary: %v", err)
		}
	}

	// Test: token-miser run --task tasks/synth-001.yaml --control vanilla --treatment ./ --model sonnet
	runCmd := exec.Command(binaryPath,
		"run",
		"--task", "tasks/synth-001.yaml",
		"--control", "vanilla",
		"--treatment", "./",
		"--model", "sonnet")
	runCmd.Dir = workDir

	runOutput, err := runCmd.CombinedOutput()
	if err != nil {
		t.Fatalf("token-miser run failed: %v\nOutput: %s", err, string(runOutput))
	}

	// Check that DB file exists after run
	dbFiles, err := filepath.Glob(filepath.Join(workDir, "*.db"))
	if err != nil {
		t.Fatalf("Failed to search for DB files: %v", err)
	}
	if len(dbFiles) == 0 {
		t.Fatal("No database file found after run")
	}

	// Wait a moment for any async operations to complete
	time.Sleep(100 * time.Millisecond)

	// Test: token-miser compare --task synth-001
	compareCmd := exec.Command(binaryPath, "compare", "--task", "synth-001")
	compareCmd.Dir = workDir

	compareOutput, err := compareCmd.CombinedOutput()
	if err != nil {
		t.Fatalf("token-miser compare failed: %v\nOutput: %s", err, string(compareOutput))
	}

	compareOutputStr := string(compareOutput)

	// Verify output mentions both "vanilla" and the treatment arm name
	if !strings.Contains(compareOutputStr, "vanilla") {
		t.Fatalf("Compare output should mention 'vanilla' control arm, got: %s", compareOutputStr)
	}

	// The treatment arm name should be the directory name or some identifier
	if !strings.Contains(compareOutputStr, "treatment") && !strings.Contains(compareOutputStr, "./") {
		t.Fatalf("Compare output should mention treatment arm, got: %s", compareOutputStr)
	}

	t.Logf("Smoke test passed successfully!")
	t.Logf("Run output: %s", string(runOutput))
	t.Logf("Compare output: %s", compareOutputStr)
}
