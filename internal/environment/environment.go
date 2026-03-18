package environment

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/rubin-johnson/token_miser/internal/arm"
	"github.com/rubin-johnson/token_miser/internal/task"
)

// Commander interface for executing shell commands
// This allows mocking in tests
type Commander interface {
	Run(command string, args []string) error
	RunWithOutput(command string, args []string) (string, error)
}

// DefaultCommander implements Commander using os/exec
type DefaultCommander struct{}

// NewDefaultCommander returns a new DefaultCommander
func NewDefaultCommander() *DefaultCommander {
	return &DefaultCommander{}
}

func (c *DefaultCommander) Run(command string, args []string) error {
	cmd := exec.Command(command, args...)
	return cmd.Run()
}

func (c *DefaultCommander) RunWithOutput(command string, args []string) (string, error) {
	cmd := exec.Command(command, args...)
	out, err := cmd.Output()
	return string(out), err
}

// EnvironmentContext represents an isolated experiment environment
type EnvironmentContext struct {
	HomeDir      string
	WorkspaceDir string
	Commander    Commander
}

// SetupEnv creates temp dir, clones repo, checks out commit
func SetupEnv(t *task.Task, a *arm.Arm, commander Commander) (*EnvironmentContext, error) {
	// Create temporary directory as HOME
	homeDir, err := os.MkdirTemp("", "experiment-*")
	if err != nil {
		return nil, fmt.Errorf("failed to create temp dir: %w", err)
	}

	repoPath := filepath.Join(homeDir, "workspace")

	env := &EnvironmentContext{
		HomeDir:      homeDir,
		WorkspaceDir: repoPath,
		Commander:    commander,
	}

	// Clone repo with --shared for speed
	err = commander.Run("git", []string{"clone", "--shared", t.Repo, repoPath})
	if err != nil {
		return nil, fmt.Errorf("failed to clone repo: %w", err)
	}

	// Checkout starting commit using -C to avoid os.Chdir
	err = commander.Run("git", []string{"-C", repoPath, "checkout", t.StartingCommit})
	if err != nil {
		return nil, fmt.Errorf("failed to checkout commit: %w", err)
	}

	// For treatment arm, apply loadout
	if a.LoadoutPath != "" {
		claudeDir := filepath.Join(homeDir, ".claude")
		err = commander.Run("loadout", []string{"apply", "--target", claudeDir, "--yes", a.LoadoutPath})
		if err != nil {
			return nil, fmt.Errorf("failed to apply loadout: %w", err)
		}
	}

	return env, nil
}

// TeardownEnv removes the entire temp dir
func (e *EnvironmentContext) TeardownEnv() error {
	if e.HomeDir == "" {
		return nil
	}
	return os.RemoveAll(e.HomeDir)
}