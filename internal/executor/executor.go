package executor

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/claudecode/internal/environment"
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

// FilterEnv strips CLAUDECODE from environment and sets HOME
func FilterEnv(env []string, homeDir string) []string {
	var filtered []string
	for _, e := range env {
		if !strings.HasPrefix(e, "CLAUDECODE=") {
			filtered = append(filtered, e)
		}
	}
	filtered = append(filtered, "HOME="+homeDir)
	return filtered
}

// RunClaude executes Claude CLI in an isolated environment
func RunClaude(prompt string, homeDir string) (*ExecutorResult, error) {
	start := time.Now()
	
	// Create isolated environment
	env := FilterEnv(os.Environ(), homeDir)
	
	// Prepare Claude CLI command
	cmd := exec.Command("claude", "--print", "--dangerously-skip-permissions", "--output-format", "json", "--no-session-persistence")
	cmd.Env = env
	cmd.Dir = homeDir
	
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
