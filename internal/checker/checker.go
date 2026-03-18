package checker

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/anthropics/claude-3-5-sonnet-20241022-experiments/internal/environment"
	"github.com/anthropics/claude-3-5-sonnet-20241022-experiments/internal/task"
)

// CheckResult represents the result of checking a criterion
type CheckResult struct {
	Passed bool
	Detail string
}

// Checker evaluates task criteria against environment context
type Checker struct {
	env *environment.EnvironmentContext
}

// New creates a new Checker with the given environment context
func New(env *environment.EnvironmentContext) *Checker {
	return &Checker{env: env}
}

// CheckCriterion evaluates a single criterion and returns the result
func (c *Checker) CheckCriterion(criterion task.Criterion) CheckResult {
	switch criterion.Type {
	case "file_exists":
		return c.checkFileExists(criterion.FilePaths)
	case "command_exits_zero":
		return c.checkCommandExitsZero(criterion.Command)
	case "output_contains":
		return c.checkOutputContains(criterion.Command, criterion.OutputContains)
	default:
		return CheckResult{
			Passed: false,
			Detail: fmt.Sprintf("unknown criterion type: %s", criterion.Type),
		}
	}
}

// CheckAllCriteria evaluates all criteria independently and returns results
func (c *Checker) CheckAllCriteria(criteria []task.Criterion) []CheckResult {
	results := make([]CheckResult, len(criteria))
	for i, criterion := range criteria {
		results[i] = c.CheckCriterion(criterion)
	}
	return results
}

func (c *Checker) checkFileExists(paths []string) CheckResult {
	var missingPaths []string
	
	for _, path := range paths {
		fullPath := filepath.Join(c.env.WorkspaceDir, path)
		if _, err := os.Stat(fullPath); os.IsNotExist(err) {
			missingPaths = append(missingPaths, path)
		}
	}
	
	if len(missingPaths) == 0 {
		return CheckResult{Passed: true}
	}
	
	return CheckResult{
		Passed: false,
		Detail: fmt.Sprintf("missing paths: %s", strings.Join(missingPaths, ", ")),
	}
}

func (c *Checker) checkCommandExitsZero(command string) CheckResult {
	cmd := exec.Command("sh", "-c", command)
	cmd.Dir = c.env.WorkspaceDir
	cmd.Env = append(os.Environ(), fmt.Sprintf("HOME=%s", c.env.HomeDir))
	
	var stderr strings.Builder
	cmd.Stderr = &stderr
	
	err := cmd.Run()
	if err != nil {
		return CheckResult{
			Passed: false,
			Detail: stderr.String(),
		}
	}
	
	return CheckResult{Passed: true}
}

func (c *Checker) checkOutputContains(command string, contains []string) CheckResult {
	cmd := exec.Command("sh", "-c", command)
	cmd.Dir = c.env.WorkspaceDir
	cmd.Env = append(os.Environ(), fmt.Sprintf("HOME=%s", c.env.HomeDir))
	
	var stdout strings.Builder
	cmd.Stdout = &stdout
	
	err := cmd.Run()
	if err != nil {
		return CheckResult{
			Passed: false,
			Detail: fmt.Sprintf("command failed: %v", err),
		}
	}
	
	output := stdout.String()
	var missingStrings []string
	
	for _, str := range contains {
		if !strings.Contains(output, str) {
			missingStrings = append(missingStrings, str)
		}
	}
	
	if len(missingStrings) == 0 {
		return CheckResult{Passed: true}
	}
	
	return CheckResult{
		Passed: false,
		Detail: fmt.Sprintf("missing strings in output: %s", strings.Join(missingStrings, ", ")),
	}
}
