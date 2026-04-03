//go:build !integration
// +build !integration

package environment

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/arm"
	"github.com/rubin-johnson/token_miser/internal/task"
)

// MockCommander for testing
type MockCommander struct {
	Commands [][]string
	Errors   map[string]error
}

func (m *MockCommander) Run(command string, args []string) error {
	cmd := append([]string{command}, args...)
	m.Commands = append(m.Commands, cmd)
	cmdStr := strings.Join(cmd, " ")
	if err, exists := m.Errors[cmdStr]; exists {
		return err
	}
	return nil
}

func (m *MockCommander) RunWithOutput(command string, args []string) (string, error) {
	cmd := append([]string{command}, args...)
	m.Commands = append(m.Commands, cmd)
	cmdStr := strings.Join(cmd, " ")
	if err, exists := m.Errors[cmdStr]; exists {
		return "", err
	}
	return "mock output", nil
}

func TestSetupEnv_VanillaArm(t *testing.T) {
	mock := &MockCommander{}
	task := &task.Task{
		Repo:           "https://github.com/example/repo.git",
		StartingCommit: "abc123",
	}
	arm := &arm.Arm{
		Name:        "vanilla",
		LoadoutPath: "",
	}

	env, err := SetupEnv(task, arm, mock)
	if err != nil {
		t.Fatalf("SetupEnv failed: %v", err)
	}
	defer env.TeardownEnv()

	// Verify temp dir was created
	if env.HomeDir == "" {
		t.Error("HomeDir should not be empty")
	}
	if _, err := os.Stat(env.HomeDir); os.IsNotExist(err) {
		t.Error("HomeDir should exist")
	}

	// Verify correct commands were called
	expectedCommands := [][]string{
		{"git", "clone", "--shared", "https://github.com/example/repo.git", filepath.Join(env.HomeDir, "workspace")},
		{"git", "-C", filepath.Join(env.HomeDir, "workspace"), "checkout", "abc123"},
	}

	if len(mock.Commands) != len(expectedCommands) {
		t.Fatalf("Expected %d commands, got %d: %v", len(expectedCommands), len(mock.Commands), mock.Commands)
	}

	for i, expected := range expectedCommands {
		if len(mock.Commands[i]) != len(expected) {
			t.Errorf("Command %d: expected %v, got %v", i, expected, mock.Commands[i])
			continue
		}
		for j, arg := range expected {
			if mock.Commands[i][j] != arg {
				t.Errorf("Command %d arg %d: expected %s, got %s", i, j, arg, mock.Commands[i][j])
			}
		}
	}
}

func TestSetupEnv_TreatmentArm(t *testing.T) {
	mock := &MockCommander{}
	task := &task.Task{
		Repo:           "https://github.com/example/repo.git",
		StartingCommit: "abc123",
	}
	arm := &arm.Arm{
		Name:        "treatment",
		LoadoutPath: "/some/loadout/bundle",
	}

	env, err := SetupEnv(task, arm, mock)
	if err != nil {
		t.Fatalf("SetupEnv failed: %v", err)
	}
	defer env.TeardownEnv()

	// Verify temp dir was created
	if env.HomeDir == "" {
		t.Error("HomeDir should not be empty")
	}

	// Verify correct commands were called including loadout
	expectedCommands := [][]string{
		{"git", "clone", "--shared", "https://github.com/example/repo.git", filepath.Join(env.HomeDir, "workspace")},
		{"git", "-C", filepath.Join(env.HomeDir, "workspace"), "checkout", "abc123"},
		{resolveLoadout(), "apply", "--target", filepath.Join(env.HomeDir, ".claude"), "--yes", "/some/loadout/bundle"},
	}

	if len(mock.Commands) != len(expectedCommands) {
		t.Fatalf("Expected %d commands, got %d", len(expectedCommands), len(mock.Commands))
	}

	for i, expected := range expectedCommands {
		if len(mock.Commands[i]) != len(expected) {
			t.Errorf("Command %d: expected %v, got %v", i, expected, mock.Commands[i])
			continue
		}
		for j, arg := range expected {
			if mock.Commands[i][j] != arg {
				t.Errorf("Command %d arg %d: expected %s, got %s", i, j, arg, mock.Commands[i][j])
			}
		}
	}
}

func TestTeardownEnv(t *testing.T) {
	mock := &MockCommander{}
	task := &task.Task{
		Repo:           "https://github.com/example/repo.git",
		StartingCommit: "abc123",
	}
	arm := &arm.Arm{
		Name:        "vanilla",
		LoadoutPath: "",
	}

	env, err := SetupEnv(task, arm, mock)
	if err != nil {
		t.Fatalf("SetupEnv failed: %v", err)
	}

	// Verify dir exists before teardown
	if _, err := os.Stat(env.HomeDir); os.IsNotExist(err) {
		t.Error("HomeDir should exist before teardown")
	}

	// Teardown
	err = env.TeardownEnv()
	if err != nil {
		t.Fatalf("TeardownEnv failed: %v", err)
	}

	// Verify dir no longer exists
	if _, err := os.Stat(env.HomeDir); !os.IsNotExist(err) {
		t.Error("HomeDir should not exist after teardown")
	}
}
