package environment

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/rubin-johnson/token_miser/internal/arm"
	"github.com/rubin-johnson/token_miser/internal/task"
)

type EnvironmentContext struct {
	HomeDir      string
	WorkspaceDir string
}

// Commander allows injecting fake exec behavior in tests.
type Commander interface {
	Run(name string, args ...string) error
}

// DefaultCommander is the exported Commander implementation that runs real subprocesses.
type DefaultCommander struct{}

// NewDefaultCommander returns a new DefaultCommander.
func NewDefaultCommander() *DefaultCommander {
	return &DefaultCommander{}
}

// Run executes the command as a subprocess and returns any error; does not capture stdout.
func (c *DefaultCommander) Run(command string, args []string) error {
	cmd := exec.Command(command, args...)
	return cmd.Run()
}

// RunWithOutput executes the command, captures stdout, and returns it along with any error.
func (c *DefaultCommander) RunWithOutput(command string, args []string) (string, error) {
	cmd := exec.Command(command, args...)
	out, err := cmd.Output()
	return string(out), err
}

type defaultCommander struct{}

func (d *defaultCommander) Run(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("command %q failed: %w\n%s", name, err, out)
	}
	return nil
}

func SetupEnv(t *task.Task, a *arm.Arm) (*EnvironmentContext, error) {
	return setupEnvWithCommander(t, a, &defaultCommander{})
}

func setupEnvWithCommander(t *task.Task, a *arm.Arm, c Commander) (*EnvironmentContext, error) {
	homeDir, err := os.MkdirTemp("", "token-miser-*")
	if err != nil {
		return nil, fmt.Errorf("create home dir: %w", err)
	}

	workspaceDir := filepath.Join(homeDir, "workspace")

	if err := c.Run("git", "clone", "--shared", t.Repo, workspaceDir); err != nil {
		_ = os.RemoveAll(homeDir)
		return nil, fmt.Errorf("git clone: %w", err)
	}

	if err := c.Run("git", "-C", workspaceDir, "checkout", t.StartingCommit); err != nil {
		_ = os.RemoveAll(homeDir)
		return nil, fmt.Errorf("git checkout: %w", err)
	}

	if a.LoadoutPath != "" {
		claudeDir := filepath.Join(homeDir, ".claude")
		if err := c.Run("loadout", "apply", "--target", claudeDir, "--yes", a.LoadoutPath); err != nil {
			_ = os.RemoveAll(homeDir)
			return nil, fmt.Errorf("loadout apply: %w", err)
		}
	}

	return &EnvironmentContext{HomeDir: homeDir, WorkspaceDir: workspaceDir}, nil
}

func TeardownEnv(ctx *EnvironmentContext) error {
	if err := os.RemoveAll(ctx.HomeDir); err != nil {
		return fmt.Errorf("remove env dir: %w", err)
	}
	return nil
}
