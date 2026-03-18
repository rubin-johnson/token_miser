package evaluator

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"path/filepath"
	"strings"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"

	"github.com/rubin-johnson/token_miser/internal/task"
)

// MessagesService defines the interface for message operations
type MessagesService interface {
	New(ctx context.Context, body anthropic.MessageNewParams, opts ...option.RequestOption) (*anthropic.Message, error)
}

// AnthropicClient defines the interface for Anthropic API calls
type AnthropicClient interface {
	Messages() MessagesService
}

// realClientAdapter wraps anthropic.Client to implement AnthropicClient
type realClientAdapter struct {
	client anthropic.Client
}

func (a *realClientAdapter) Messages() MessagesService {
	return &a.client.Messages
}

// DimensionScore represents a score for a single rubric dimension
type DimensionScore struct {
	Dimension task.RubricDimension `json:"dimension"`
	Score     float64              `json:"score"`
	Reason    string               `json:"reason"`
}

// Evaluator handles quality scoring using LLM judge
type Evaluator struct {
	client AnthropicClient
}

// NewEvaluator creates a new evaluator with Anthropic client
func NewEvaluator(apiKey string) *Evaluator {
	client := anthropic.NewClient(option.WithAPIKey(apiKey))
	return &Evaluator{
		client: &realClientAdapter{client: client},
	}
}

// ScoreQuality evaluates Claude's output quality across multiple dimensions
func (e *Evaluator) ScoreQuality(ctx context.Context, input, output string, dimensions []task.RubricDimension) ([]DimensionScore, error) {
	// Collect workspace files for context
	workspaceContext, err := e.collectWorkspaceFiles()
	if err != nil {
		return nil, fmt.Errorf("failed to collect workspace files: %w", err)
	}

	// Build judge prompt
	prompt := e.buildJudgePrompt(input, output, dimensions, workspaceContext)

	// Call Haiku model
	resp, err := e.client.Messages().New(ctx, anthropic.MessageNewParams{
		Model:     anthropic.ModelClaude_3_Haiku_20240307,
		MaxTokens: 2000,
		Messages: []anthropic.MessageParam{
			anthropic.NewUserMessage(anthropic.NewTextBlock(prompt)),
		},
	})
	if err != nil {
		return nil, fmt.Errorf("failed to call Anthropic API: %w", err)
	}

	// Extract text content from response
	textContent, err := e.extractTextContent(resp)
	if err != nil {
		return nil, err
	}

	// Parse JSON response
	var scores []DimensionScore
	if err := json.Unmarshal([]byte(textContent), &scores); err != nil {
		return nil, fmt.Errorf("failed to parse JSON response: %w", err)
	}

	// Validate scores
	for i, score := range scores {
		if score.Score < 0.0 || score.Score > 1.0 {
			return nil, fmt.Errorf("score %d out of range [0.0, 1.0]: %f", i, score.Score)
		}
		if score.Reason == "" {
			return nil, fmt.Errorf("score %d has empty reason", i)
		}
	}

	return scores, nil
}

// extractTextContent extracts text content from Anthropic response
func (e *Evaluator) extractTextContent(resp *anthropic.Message) (string, error) {
	if len(resp.Content) == 0 {
		return "", fmt.Errorf("empty response from Anthropic API")
	}

	for _, content := range resp.Content {
		if content.Type == "text" {
			return content.Text, nil
		}
	}

	return "", fmt.Errorf("no text content in response")
}

// collectWorkspaceFiles gathers relevant files for context, skipping hidden dirs and common exclusions
func (e *Evaluator) collectWorkspaceFiles() (string, error) {
	var files []string

	err := filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		// Skip hidden directories and common exclusions
		if d.IsDir() {
			name := d.Name()
			if strings.HasPrefix(name, ".") || name == "vendor" || name == "node_modules" {
				return filepath.SkipDir
			}
			return nil
		}

		// Only include relevant file types
		ext := filepath.Ext(path)
		if ext == ".go" || ext == ".md" || ext == ".txt" || ext == ".json" || ext == ".yaml" || ext == ".yml" {
			files = append(files, path)
		}

		return nil
	})

	if err != nil {
		return "", err
	}

	// Build context string (limit to avoid token overflow)
	var context strings.Builder
	context.WriteString("Workspace files:\n")
	for i, file := range files {
		if i >= 50 { // Limit number of files
			context.WriteString("... (truncated)\n")
			break
		}
		context.WriteString(fmt.Sprintf("- %s\n", file))
	}

	return context.String(), nil
}

// buildJudgePrompt constructs the prompt for the LLM judge
func (e *Evaluator) buildJudgePrompt(input, output string, dimensions []task.RubricDimension, workspaceContext string) string {
	var prompt strings.Builder

	prompt.WriteString("You are an expert evaluator judging the quality of Claude's output.\n\n")
	prompt.WriteString("Context:\n")
	prompt.WriteString(workspaceContext)
	prompt.WriteString("\n")

	prompt.WriteString("Input:\n")
	prompt.WriteString(input)
	prompt.WriteString("\n\n")

	prompt.WriteString("Output to evaluate:\n")
	prompt.WriteString(output)
	prompt.WriteString("\n\n")

	prompt.WriteString("Please score the output on the following dimensions (0.0-1.0 scale):\n")
	for _, dim := range dimensions {
		prompt.WriteString(fmt.Sprintf("- %s: %s\n", dim.Dimension, dim.Prompt))
	}

	prompt.WriteString("\nRespond with a JSON array of scores in this exact format:\n")
	prompt.WriteString("[\n")
	prompt.WriteString("  {\n")
	prompt.WriteString("    \"dimension\": {\"name\": \"dimension_name\", \"description\": \"dimension_description\"},\n")
	prompt.WriteString("    \"score\": 0.85,\n")
	prompt.WriteString("    \"reason\": \"Detailed explanation for the score\"\n")
	prompt.WriteString("  }\n")
	prompt.WriteString("]\n")

	return prompt.String()
}
