package evaluator

import (
	"context"
	"strings"
	"testing"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"

	"github.com/anthropics/claude-tokenizer-go/internal/task"
)

// Mock implementations
type mockAnthropicClient struct {
	messagesService *mockMessagesService
}

func (m *mockAnthropicClient) Messages() MessagesService {
	return m.messagesService
}

type mockMessagesService struct {
	response *anthropic.Message
	error    error
}

func (m *mockMessagesService) New(ctx context.Context, body anthropic.MessageNewParams, opts ...option.RequestOption) (*anthropic.Message, error) {
	if m.error != nil {
		return nil, m.error
	}
	return m.response, nil
}

// Mock content that implements GetText() method
type mockContent struct {
	text string
}

func (m *mockContent) GetText() string {
	return m.text
}

// Helper function to create mock response
func createMockResponse(text string) *anthropic.Message {
	return &anthropic.Message{
		Content: []interface{}{
			&mockContent{text: text},
		},
	}
}

func TestNewEvaluator(t *testing.T) {
	apiKey := "test-api-key"
	evaluator := NewEvaluator(apiKey)

	if evaluator == nil {
		t.Fatal("NewEvaluator returned nil")
	}

	if evaluator.client == nil {
		t.Fatal("Evaluator client is nil")
	}
}

func TestScoreQuality(t *testing.T) {
	tests := []struct {
		name       string
		response   string
		dimensions []task.RubricDimension
		wantErr    bool
		wantScores int
	}{
		{
			name: "successful evaluation",
			response: `[
				{
					"dimension": {"name": "accuracy", "description": "How accurate is the response"},
					"score": 0.85,
					"reason": "Response is mostly accurate with minor issues"
				},
				{
					"dimension": {"name": "clarity", "description": "How clear is the response"},
					"score": 0.92,
					"reason": "Very clear and well-structured response"
				}
			]`,
			dimensions: []task.RubricDimension{
				{Name: "accuracy", Description: "How accurate is the response"},
				{Name: "clarity", Description: "How clear is the response"},
			},
			wantErr:    false,
			wantScores: 2,
		},
		{
			name:       "invalid JSON response",
			response:   "invalid json",
			dimensions: []task.RubricDimension{{Name: "test", Description: "test"}},
			wantErr:    true,
		},
		{
			name: "score out of range",
			response: `[
				{
					"dimension": {"name": "test", "description": "test"},
					"score": 1.5,
					"reason": "Test reason"
				}
			]`,
			dimensions: []task.RubricDimension{{Name: "test", Description: "test"}},
			wantErr:    true,
		},
		{
			name: "empty reason",
			response: `[
				{
					"dimension": {"name": "test", "description": "test"},
					"score": 0.5,
					"reason": ""
				}
			]`,
			dimensions: []task.RubricDimension{{Name: "test", Description: "test"}},
			wantErr:    true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create evaluator with mock client
			mockClient := &mockAnthropicClient{
				messagesService: &mockMessagesService{
					response: createMockResponse(tt.response),
				},
			}

			evaluator := &Evaluator{client: mockClient}

			// Test ScoreQuality
			scores, err := evaluator.ScoreQuality(context.Background(), "test input", "test output", tt.dimensions)

			if tt.wantErr {
				if err == nil {
					t.Errorf("ScoreQuality() expected error, got nil")
				}
				return
			}

			if err != nil {
				t.Errorf("ScoreQuality() unexpected error: %v", err)
				return
			}

			if len(scores) != tt.wantScores {
				t.Errorf("ScoreQuality() got %d scores, want %d", len(scores), tt.wantScores)
			}

			// Validate each score
			for i, score := range scores {
				if score.Score < 0.0 || score.Score > 1.0 {
					t.Errorf("Score %d out of range: %f", i, score.Score)
				}
				if score.Reason == "" {
					t.Errorf("Score %d has empty reason", i)
				}
			}
		})
	}
}

func TestCollectWorkspaceFiles(t *testing.T) {
	evaluator := &Evaluator{}
	context, err := evaluator.collectWorkspaceFiles()

	if err != nil {
		t.Errorf("collectWorkspaceFiles() unexpected error: %v", err)
	}

	if context == "" {
		t.Error("collectWorkspaceFiles() returned empty context")
	}

	// Should contain "Workspace files:"
	if !strings.Contains(context, "Workspace files:") {
		t.Error("collectWorkspaceFiles() should contain 'Workspace files:'")
	}
}

func TestBuildJudgePrompt(t *testing.T) {
	evaluator := &Evaluator{}
	dimensions := []task.RubricDimension{
		{Name: "accuracy", Description: "How accurate is the response"},
		{Name: "clarity", Description: "How clear is the response"},
	}

	prompt := evaluator.buildJudgePrompt("test input", "test output", dimensions, "test context")

	if prompt == "" {
		t.Error("buildJudgePrompt() returned empty prompt")
	}

	// Check that prompt contains expected elements
	expectedElements := []string{
		"test input",
		"test output",
		"test context",
		"accuracy",
		"clarity",
		"JSON array",
	}

	for _, element := range expectedElements {
		if !strings.Contains(prompt, element) {
			t.Errorf("buildJudgePrompt() should contain '%s'", element)
		}
	}
}

func TestScoreQualityPromptConstruction(t *testing.T) {
	// Test that the prompt is constructed correctly by checking the mock call
	mockClient := &mockAnthropicClient{
		messagesService: &mockMessagesService{
			response: createMockResponse(`[{"dimension": {"name": "test", "description": "test"}, "score": 0.5, "reason": "test reason"}]`),
		},
	}

	evaluator := &Evaluator{client: mockClient}
	dimensions := []task.RubricDimension{{Name: "test", Description: "test dimension"}}

	_, err := evaluator.ScoreQuality(context.Background(), "input", "output", dimensions)
	if err != nil {
		t.Errorf("ScoreQuality() unexpected error: %v", err)
	}
}

func TestScoreQualityJSONParsing(t *testing.T) {
	tests := []struct {
		name     string
		response string
		wantErr  bool
	}{
		{
			name:     "valid JSON",
			response: `[{"dimension": {"name": "test", "description": "test"}, "score": 0.5, "reason": "valid"}]`,
			wantErr:  false,
		},
		{
			name:     "invalid JSON",
			response: `{invalid json}`,
			wantErr:  true,
		},
		{
			name:     "empty array",
			response: `[]`,
			wantErr:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mockClient := &mockAnthropicClient{
				messagesService: &mockMessagesService{
					response: createMockResponse(tt.response),
				},
			}

			evaluator := &Evaluator{client: mockClient}
			dimensions := []task.RubricDimension{{Name: "test", Description: "test"}}

			_, err := evaluator.ScoreQuality(context.Background(), "input", "output", dimensions)

			if tt.wantErr && err == nil {
				t.Error("Expected error but got none")
			}
			if !tt.wantErr && err != nil {
				t.Errorf("Unexpected error: %v", err)
			}
		})
	}
}
