package cmd

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

func TestSmokeTest(t *testing.T) {
	// Build the binary
	cmd := exec.Command("go", "build", "-o", "token-miser", "./token-miser/")
	cmd.Dir = "."
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to build binary: %v", err)
	}

	// Clean up binary after test
	defer func() {
		os.Remove("token-miser")
	}()

	// Test --help flag
	cmd = exec.Command("./token-miser", "--help")
	cmd.Dir = "."
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("token-miser --help failed: %v", err)
	}

	outputStr := string(output)
	requiredSubcommands := []string{"run", "compare", "history", "tasks"}
	for _, subcmd := range requiredSubcommands {
		if !strings.Contains(outputStr, subcmd) {
			t.Errorf("Help output missing subcommand '%s'. Output: %s", subcmd, outputStr)
		}
	}
}
