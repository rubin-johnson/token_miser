package environment

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/anthropics/loadout/internal/arm"
	"github.com/anthropics/loadout/internal/task"
)

// Commander interface for executing shell commands
// This allows mocking in tests
type Commander interface {
	Run(command string, args ...string) error
	RunWithOutput(command string, args ...string) (string, error)
}

// DefaultCommander implements Commander using os/exec
type DefaultCommander struct{}

func (c *DefaultCommander) Run(command string, args ...string) error {
	// Implementation would use os/exec.Command
	panic("not implemented")
}

func (c *DefaultCommander) RunWithOutput(command string, args ...string) (string, error) {
	// Implementation would use os/exec.Command
	panic("not implemented")
}

// Environment represents an isolated experiment environment
type Environment struct {
	HomeDir   string
	Commander Commander
}

// SetupEnv creates temp dir, clones repo, checks out commit
func SetupEnv(t *task.Task, a *arm.Arm, commander Commander) (*Environment, error) {
	// Create temporary directory as HOME
	homeDir, err := os.MkdirTemp("", "experiment-*")
	if err != nil {
		return nil, fmt.Errorf("failed to create temp dir: %w", err)
	}

	env := &Environment{
		HomeDir:   homeDir,
		Commander: commander,
	}

	// Clone repo with --shared for speed
	repoPath := filepath.Join(homeDir, "workspace")
	err = commander.Run("git", "clone", "--shared", t.RepoURL, repoPath)
	if err != nil {
		return nil, fmt.Errorf("failed to clone repo: %w", err)
	}

	// Change to repo directory and checkout starting commit
	oldDir, err := os.Getwd()
	if err != nil {
		return nil, fmt.Errorf("failed to get current dir: %w", err)
	}
	defer os.Chdir(oldDir)

	err = os.Chdir(repoPath)
	if err != nil {
		return nil, fmt.Errorf("failed to change to repo dir: %w", err)
	}

	err = commander.Run("git", "checkout", t.StartingCommit)
	if err != nil {
		return nil, fmt.Errorf("failed to checkout commit: %w", err)
	}

	// For treatment arm, apply loadout
	if a.Type == arm.TypeTreatment {
		claudeDir := filepath.Join(homeDir, ".claude")
		// TODO: Get loadout bundle from task or arm configuration
		loadoutBundle := "default-bundle.tar.gz" // placeholder
		err = commander.Run("loadout", "apply", "--target", claudeDir, "--yes", loadoutBundle)
		if err != nil {
			return nil, fmt.Errorf("failed to apply loadout: %w", err)
		}
	}

	return env, nil
}

// TeardownEnv removes the entire temp dir
func (e *Environment) TeardownEnv() error {
	if e.HomeDir == "" {
		return nil
	}
	return os.RemoveAll(e.HomeDir)
}
