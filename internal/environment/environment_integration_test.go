//go:build integration
// +build integration

package environment

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/anthropics/loadout/internal/arm"
	"github.com/anthropics/loadout/internal/task"
)

// RealCommander implements Commander using os/exec
type RealCommander struct{}

func (c *RealCommander) Run(command string, args ...string) error {
	cmd := exec.Command(command, args...)
	return cmd.Run()
}

func (c *RealCommander) RunWithOutput(command string, args ...string) (string, error) {
	cmd := exec.Command(command, args...)
	output, err := cmd.Output()
	return string(output), err
}

func TestSetupEnv_Integration(t *testing.T) {
	// Skip if git is not available
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available, skipping integration test")
	}

	commander := &RealCommander{}
	task := &task.Task{
		RepoURL:        "https://github.com/anthropics/loadout.git",
		StartingCommit: "fd88685",
	}
	arm := &arm.Arm{
		Type: arm.TypeVanilla,
	}

	env, err := SetupEnv(task, arm, commander)
	if err != nil {
		t.Fatalf("SetupEnv failed: %v", err)
	}
	defer env.TeardownEnv()

	// Verify the workspace was created
	workspacePath := filepath.Join(env.HomeDir, "workspace")
	if _, err := os.Stat(workspacePath); os.IsNotExist(err) {
		t.Error("Workspace directory should exist")
	}

	// Verify docs/design-notes.md exists in workspace
	designNotesPath := filepath.Join(workspacePath, "docs", "design-notes.md")
	if _, err := os.Stat(designNotesPath); os.IsNotExist(err) {
		t.Error("docs/design-notes.md should exist in workspace")
	}

	// Verify we're on the correct commit
	oldDir, err := os.Getwd()
	if err != nil {
		t.Fatalf("Failed to get current dir: %v", err)
	}
	defer os.Chdir(oldDir)

	err = os.Chdir(workspacePath)
	if err != nil {
		t.Fatalf("Failed to change to workspace dir: %v", err)
	}

	output, err := commander.RunWithOutput("git", "rev-parse", "HEAD")
	if err != nil {
		t.Fatalf("Failed to get current commit: %v", err)
	}

	if output[:7] != "fd88685" {
		t.Errorf("Expected commit to start with fd88685, got %s", output)
	}
}
