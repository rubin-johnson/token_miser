package checker

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/rubin-johnson/token_miser/internal/environment"
	"github.com/rubin-johnson/token_miser/internal/task"
)

type CriterionResult struct {
	Type   string
	Passed bool
	Detail string
}

func EvaluateCriteria(criteria []task.Criterion, env *environment.EnvironmentContext) []CriterionResult {
	results := make([]CriterionResult, 0, len(criteria))
	for _, c := range criteria {
		results = append(results, evaluate(c, env))
	}
	return results
}

func evaluate(c task.Criterion, env *environment.EnvironmentContext) CriterionResult {
	switch c.Type {
	case "file_exists":
		return evaluateFileExists(c, env)
	case "command_exits_zero":
		return evaluateCommandExitsZero(c, env)
	case "output_contains":
		return evaluateOutputContains(c, env)
	default:
		return CriterionResult{Type: c.Type, Passed: false, Detail: fmt.Sprintf("unknown criterion type: %s", c.Type)}
	}
}

func evaluateFileExists(c task.Criterion, env *environment.EnvironmentContext) CriterionResult {
	for _, p := range c.Paths {
		full := filepath.Join(env.WorkspaceDir, p)
		if _, err := os.Stat(full); err != nil {
			return CriterionResult{Type: c.Type, Passed: false, Detail: fmt.Sprintf("missing: %s", p)}
		}
	}
	return CriterionResult{Type: c.Type, Passed: true, Detail: "all files exist"}
}

func evaluateCommandExitsZero(c task.Criterion, env *environment.EnvironmentContext) CriterionResult {
	cmd := exec.Command("sh", "-c", c.Command)
	cmd.Dir = env.WorkspaceDir
	cmd.Env = append(os.Environ(), fmt.Sprintf("HOME=%s", env.HomeDir))
	out, err := cmd.CombinedOutput()
	if err != nil {
		return CriterionResult{Type: c.Type, Passed: false, Detail: strings.TrimSpace(string(out))}
	}
	return CriterionResult{Type: c.Type, Passed: true, Detail: "exit 0"}
}

func evaluateOutputContains(c task.Criterion, env *environment.EnvironmentContext) CriterionResult {
	cmd := exec.Command("sh", "-c", c.Command)
	cmd.Dir = env.WorkspaceDir
	cmd.Env = append(os.Environ(), fmt.Sprintf("HOME=%s", env.HomeDir))
	out, err := cmd.Output()
	if err != nil {
		return CriterionResult{Type: c.Type, Passed: false, Detail: fmt.Sprintf("command failed: %v", err)}
	}
	stdout := string(out)
	for _, s := range c.Contains {
		if !strings.Contains(stdout, s) {
			return CriterionResult{Type: c.Type, Passed: false, Detail: fmt.Sprintf("missing %q in output", s)}
		}
	}
	return CriterionResult{Type: c.Type, Passed: true, Detail: "all strings found"}
}
