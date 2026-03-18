package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

func TestSmokeTest(t *testing.T) {
	// Build the binary
	cmd := exec.Command("go", "build", "-o", "token-miser", "./token-miser")
	cmd.Dir = "."
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to build binary: %v", err)
	}
	defer os.Remove("token-miser")

	// Test --help flag
	cmd = exec.Command("./token-miser", "--help")
	cmd.Dir = "."
	output, err := cmd.CombinedOutput()
	if err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			if exitError.ExitCode() != 0 {
				t.Fatalf("Expected exit code 0, got %d. Output: %s", exitError.ExitCode(), string(output))
			}
		} else {
			t.Fatalf("Failed to run --help: %v", err)
		}
	}

	// Check that all required subcommands are mentioned in help output
	outputStr := string(output)
	requiredCommands := []string{"run", "compare", "history", "tasks"}
	for _, cmd := range requiredCommands {
		if !strings.Contains(outputStr, cmd) {
			t.Errorf("Help output missing command: %s\nOutput: %s", cmd, outputStr)
		}
	}
}
