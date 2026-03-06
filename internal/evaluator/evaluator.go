package evaluator

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"
	"github.com/rubin-johnson/token_miser/internal/task"
)

type DimensionScore struct {
	Dimension string
	Score     float64
	Reason    string
}

type Evaluator struct {
	client anthropic.Client
}

func NewEvaluator(apiKey string) *Evaluator {
	if apiKey == "" {
		return nil
	}
	client := anthropic.NewClient(option.WithAPIKey(apiKey))
	return &Evaluator{client: client}
}

type judgeResponse struct {
	Score  float64 `json:"score"`
	Reason string  `json:"reason"`
}

func ScoreQuality(ctx context.Context, e *Evaluator, rubric []task.RubricDimension, taskPrompt string, workspaceDir string) ([]DimensionScore, error) {
	if e == nil {
		return nil, nil
	}

	codeExcerpt := readWorkspaceFiles(workspaceDir)

	scores := make([]DimensionScore, 0, len(rubric))
	for _, dim := range rubric {
		score, err := scoreDimension(ctx, e, dim, taskPrompt, codeExcerpt)
		if err != nil {
			return scores, fmt.Errorf("score dimension %q: %w", dim.Dimension, err)
		}
		scores = append(scores, score)
	}
	return scores, nil
}

func scoreDimension(ctx context.Context, e *Evaluator, dim task.RubricDimension, taskPrompt, codeExcerpt string) (DimensionScore, error) {
	userPrompt := fmt.Sprintf("Task: %s\n\nCode:\n%s\n\nQuestion: %s\n\nRespond with {\"score\": 0.0-1.0, \"reason\": \"...\"}",
		taskPrompt, codeExcerpt, dim.Prompt)

	msg, err := e.client.Messages.New(ctx, anthropic.MessageNewParams{
		Model:     anthropic.ModelClaudeHaiku4_5_20251001,
		MaxTokens: 256,
		System: []anthropic.TextBlockParam{
			{Text: "You are a code quality judge. Respond only with JSON."},
		},
		Messages: []anthropic.MessageParam{
			{Role: anthropic.MessageParamRoleUser, Content: []anthropic.ContentBlockParamUnion{
				anthropic.NewTextBlock(userPrompt),
			}},
		},
	})
	if err != nil {
		return DimensionScore{}, fmt.Errorf("call anthropic: %w", err)
	}

	var raw string
	for _, block := range msg.Content {
		if block.Type == "text" {
			raw = block.Text
			break
		}
	}

	var resp judgeResponse
	if err := json.Unmarshal([]byte(raw), &resp); err != nil {
		return DimensionScore{}, fmt.Errorf("parse judge response: %w", err)
	}

	return DimensionScore{Dimension: dim.Dimension, Score: resp.Score, Reason: resp.Reason}, nil
}

func readWorkspaceFiles(dir string) string {
	var parts []string
	count := 0
	const maxFiles = 5
	const maxChars = 4000

	_ = filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil || count >= maxFiles {
			return nil
		}
		if d.IsDir() {
			name := d.Name()
			if strings.HasPrefix(name, ".") || name == "vendor" || name == "node_modules" {
				return filepath.SkipDir
			}
			return nil
		}
		data, readErr := os.ReadFile(path)
		if readErr != nil {
			return nil
		}
		text := string(data)
		if len(text) > maxChars {
			text = text[:maxChars]
		}
		rel, _ := filepath.Rel(dir, path)
		parts = append(parts, fmt.Sprintf("=== %s ===\n%s", rel, text))
		count++
		return nil
	})

	return strings.Join(parts, "\n\n")
}
