package executor

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

)

// ExecutorResult represents the result of running Claude CLI
type ExecutorResult struct {
	Result       string  `json:"result"`
	TotalCostUSD float64 `json:"total_cost_usd"`
	Usage        Usage   `json:"usage"`
	WallSeconds  float64 `json:"wall_seconds"`
}

// Usage represents token usage information
type Usage struct {
	InputTokens              int `json:"input_tokens"`
	OutputTokens             int `json:"output_tokens"`
	CacheCreationInputTokens int `json:"cache_creation_input_tokens"`
	CacheReadInputTokens     int `json:"cache_read_input_tokens"`
}

// ParseClaudeJSON parses Claude CLI JSON output into ExecutorResult
func ParseClaudeJSON(jsonData []byte) (*ExecutorResult, error) {
	var result ExecutorResult
	err := json.Unmarshal(jsonData, &result)
	if err != nil {
		return nil, fmt.Errorf("failed to parse JSON: %w", err)
	}
	return &result, nil
}

// FilterEnv strips session state from environment, sets HOME, and forwards auth vars.
// Auth tokens (CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_*) are forwarded so the subprocess
// can authenticate. Session state (CLAUDECODE) is stripped to prevent contamination.
func FilterEnv(env []string, homeDir string) []string {
	var filtered []string
	homeSet := false
	for _, e := range env {
		switch {
		case strings.HasPrefix(e, "CLAUDECODE="):
			// strip session marker
		case strings.HasPrefix(e, "HOME="):
			filtered = append(filtered, "HOME="+homeDir)
			homeSet = true
		default:
			filtered = append(filtered, e)
		}
	}
	if !homeSet {
		filtered = append(filtered, "HOME="+homeDir)
	}
	return filtered
}

// SequentialResult holds the per-prompt results and an accumulated total.
type SequentialResult struct {
	Steps []*ExecutorResult
	Total ExecutorResult // summed cost/tokens, last step's Result text
}

// RunClaudeSequential runs multiple prompts sequentially in the same HOME directory.
// Memories and session state written by earlier prompts are visible to later ones,
// which is the key property needed to test cross-session memory tools.
func RunClaudeSequential(prompts []string, homeDir string, workspaceDir string) (*SequentialResult, error) {
	sr := &SequentialResult{}
	wallStart := time.Now()

	for _, prompt := range prompts {
		res, err := RunClaude(prompt, homeDir, workspaceDir)
		if err != nil {
			return nil, fmt.Errorf("prompt %d failed: %w", len(sr.Steps)+1, err)
		}
		sr.Steps = append(sr.Steps, res)
		sr.Total.TotalCostUSD += res.TotalCostUSD
		sr.Total.Usage.InputTokens += res.Usage.InputTokens
		sr.Total.Usage.OutputTokens += res.Usage.OutputTokens
		sr.Total.Usage.CacheCreationInputTokens += res.Usage.CacheCreationInputTokens
		sr.Total.Usage.CacheReadInputTokens += res.Usage.CacheReadInputTokens
		sr.Total.Result = res.Result // keep last step's output
	}

	sr.Total.WallSeconds = time.Since(wallStart).Seconds()
	return sr, nil
}

// RunClaude executes Claude CLI in an isolated environment with CWD set to workspaceDir.
func RunClaude(prompt string, homeDir string, workspaceDir string) (*ExecutorResult, error) {
	start := time.Now()

	// Create isolated environment
	env := FilterEnv(os.Environ(), homeDir)

	// Prepare Claude CLI command
	cmd := exec.Command("claude", "--print", "--dangerously-skip-permissions", "--output-format", "json", "--no-session-persistence")
	cmd.Env = env
	cmd.Dir = workspaceDir
	
	// Set up stdin with prompt
	cmd.Stdin = strings.NewReader(prompt)
	
	// Execute command
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("claude command failed: %w", err)
	}
	
	// Parse JSON output
	result, err := ParseClaudeJSON(output)
	if err != nil {
		return nil, err
	}
	
	// Set wall time
	result.WallSeconds = time.Since(start).Seconds()
	
	return result, nil
}
