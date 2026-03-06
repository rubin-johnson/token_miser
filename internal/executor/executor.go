package executor

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/rubin-johnson/token_miser/internal/environment"
)

type ExecutorResult struct {
	ResultText      string
	InputTokens     int
	OutputTokens    int
	CacheReadTokens int
	CacheWriteTokens int
	TotalCostUSD    float64
	WallSeconds     float64
	ExitCode        int
}

type claudeUsage struct {
	InputTokens            int `json:"input_tokens"`
	OutputTokens           int `json:"output_tokens"`
	CacheReadInputTokens   int `json:"cache_read_input_tokens"`
	CacheCreationInputTokens int `json:"cache_creation_input_tokens"`
}

type claudeJSON struct {
	Result      string      `json:"result"`
	TotalCostUSD float64   `json:"total_cost_usd"`
	Usage       claudeUsage `json:"usage"`
}

func ParseClaudeJSON(raw string) (*ExecutorResult, error) {
	var parsed claudeJSON
	if err := json.Unmarshal([]byte(raw), &parsed); err != nil {
		excerpt := raw
		if len(excerpt) > 200 {
			excerpt = excerpt[:200] + "..."
		}
		return nil, fmt.Errorf("parse claude JSON: %w\nraw: %s", err, excerpt)
	}
	return &ExecutorResult{
		ResultText:       parsed.Result,
		InputTokens:      parsed.Usage.InputTokens,
		OutputTokens:     parsed.Usage.OutputTokens,
		CacheReadTokens:  parsed.Usage.CacheReadInputTokens,
		CacheWriteTokens: parsed.Usage.CacheCreationInputTokens,
		TotalCostUSD:     parsed.TotalCostUSD,
	}, nil
}

func filterEnv(environ []string) []string {
	filtered := make([]string, 0, len(environ))
	for _, e := range environ {
		if !strings.HasPrefix(e, "CLAUDECODE=") {
			filtered = append(filtered, e)
		}
	}
	return filtered
}

func RunClaude(ctx context.Context, prompt string, env *environment.EnvironmentContext, model string) (*ExecutorResult, error) {
	promptFile := fmt.Sprintf("%s/prompt.txt", env.HomeDir)
	if err := os.WriteFile(promptFile, []byte(prompt), 0600); err != nil {
		return nil, fmt.Errorf("write prompt file: %w", err)
	}

	f, err := os.Open(promptFile)
	if err != nil {
		return nil, fmt.Errorf("open prompt file: %w", err)
	}
	defer f.Close()

	envVars := filterEnv(os.Environ())
	envVars = append(envVars, fmt.Sprintf("HOME=%s", env.HomeDir))

	cmd := exec.CommandContext(ctx, "claude", "--print",
		"--dangerously-skip-permissions",
		"--output-format", "json",
		"--model", model,
		"--no-session-persistence",
	)
	cmd.Stdin = f
	cmd.Dir = env.WorkspaceDir
	cmd.Env = envVars

	start := time.Now()
	out, err := cmd.Output()
	elapsed := time.Since(start).Seconds()

	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			return nil, fmt.Errorf("run claude: %w", err)
		}
	}

	result, parseErr := ParseClaudeJSON(string(out))
	if parseErr != nil {
		return nil, parseErr
	}
	result.WallSeconds = elapsed
	result.ExitCode = exitCode
	return result, nil
}
