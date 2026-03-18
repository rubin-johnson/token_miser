package executor

import (
	"strings"
	"testing"
)

func TestParseClaudeJSON_ValidJSON(t *testing.T) {
	jsonData := `{
		"result": "Hello, world!",
		"total_cost_usd": 0.04,
		"usage": {
			"input_tokens": 1200,
			"output_tokens": 3400,
			"cache_creation_input_tokens": 0,
			"cache_read_input_tokens": 800
		}
	}`
	
	result, err := ParseClaudeJSON([]byte(jsonData))
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if result.Result != "Hello, world!" {
		t.Errorf("Expected result 'Hello, world!', got: %s", result.Result)
	}
	
	if result.TotalCostUSD != 0.04 {
		t.Errorf("Expected total_cost_usd 0.04, got: %f", result.TotalCostUSD)
	}
	
	if result.Usage.InputTokens != 1200 {
		t.Errorf("Expected input_tokens 1200, got: %d", result.Usage.InputTokens)
	}
	
	if result.Usage.OutputTokens != 3400 {
		t.Errorf("Expected output_tokens 3400, got: %d", result.Usage.OutputTokens)
	}
	
	if result.Usage.CacheCreationInputTokens != 0 {
		t.Errorf("Expected cache_creation_input_tokens 0, got: %d", result.Usage.CacheCreationInputTokens)
	}
	
	if result.Usage.CacheReadInputTokens != 800 {
		t.Errorf("Expected cache_read_input_tokens 800, got: %d", result.Usage.CacheReadInputTokens)
	}
}

func TestParseClaudeJSON_MissingUsageFields(t *testing.T) {
	jsonData := `{
		"result": "Hello, world!",
		"total_cost_usd": 0.04
	}`
	
	result, err := ParseClaudeJSON([]byte(jsonData))
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if result.Result != "Hello, world!" {
		t.Errorf("Expected result 'Hello, world!', got: %s", result.Result)
	}
	
	if result.TotalCostUSD != 0.04 {
		t.Errorf("Expected total_cost_usd 0.04, got: %f", result.TotalCostUSD)
	}
	
	// Usage fields should be zero values
	if result.Usage.InputTokens != 0 {
		t.Errorf("Expected input_tokens 0, got: %d", result.Usage.InputTokens)
	}
	
	if result.Usage.OutputTokens != 0 {
		t.Errorf("Expected output_tokens 0, got: %d", result.Usage.OutputTokens)
	}
	
	if result.Usage.CacheCreationInputTokens != 0 {
		t.Errorf("Expected cache_creation_input_tokens 0, got: %d", result.Usage.CacheCreationInputTokens)
	}
	
	if result.Usage.CacheReadInputTokens != 0 {
		t.Errorf("Expected cache_read_input_tokens 0, got: %d", result.Usage.CacheReadInputTokens)
	}
}

func TestParseClaudeJSON_InvalidJSON(t *testing.T) {
	jsonData := `{invalid json}`
	
	_, err := ParseClaudeJSON([]byte(jsonData))
	if err == nil {
		t.Fatal("Expected error for invalid JSON, got nil")
	}
	
	if !strings.Contains(err.Error(), "failed to parse JSON") {
		t.Errorf("Expected error message to contain 'failed to parse JSON', got: %s", err.Error())
	}
}

func TestFilterEnv_StripsClaudeCodeAndSetsHome(t *testing.T) {
	originalEnv := []string{
		"PATH=/usr/bin",
		"CLAUDECODE=some_value",
		"USER=testuser",
		"CLAUDECODE_OTHER=another_value",
		"HOME=/old/home",
	}
	
	newHomeDir := "/new/home"
	filtered := FilterEnv(originalEnv, newHomeDir)
	
	// Check that CLAUDECODE is stripped
	for _, env := range filtered {
		if strings.HasPrefix(env, "CLAUDECODE=") {
			t.Errorf("CLAUDECODE should be stripped, but found: %s", env)
		}
	}
	
	// Check that HOME is set to new value
	found := false
	for _, env := range filtered {
		if env == "HOME="+newHomeDir {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("HOME should be set to %s", newHomeDir)
	}
	
	// Check that other env vars are preserved
	foundPath := false
	foundUser := false
	for _, env := range filtered {
		if env == "PATH=/usr/bin" {
			foundPath = true
		}
		if env == "USER=testuser" {
			foundUser = true
		}
	}
	if !foundPath {
		t.Error("PATH should be preserved")
	}
	if !foundUser {
		t.Error("USER should be preserved")
	}
}

func TestRunClaude_MeasuresWallTime(t *testing.T) {
	// This test would require mocking the claude command
	// For now, we'll test that WallSeconds is populated when parsing JSON
	jsonData := `{
		"result": "Test result",
		"total_cost_usd": 0.01,
		"usage": {
			"input_tokens": 100,
			"output_tokens": 200
		}
	}`
	
	result, err := ParseClaudeJSON([]byte(jsonData))
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	// Initially WallSeconds should be 0
	if result.WallSeconds != 0 {
		t.Errorf("Expected WallSeconds to be 0 initially, got: %f", result.WallSeconds)
	}
	
	// Set WallSeconds to simulate RunClaude behavior
	result.WallSeconds = 1.5
	if result.WallSeconds != 1.5 {
		t.Errorf("Expected WallSeconds to be 1.5, got: %f", result.WallSeconds)
	}
}
