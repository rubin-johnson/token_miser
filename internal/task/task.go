package task

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// Task represents a task definition loaded from YAML
type Task struct {
	ID              string            `yaml:"id"`
	Name            string            `yaml:"name"`
	Type            string            `yaml:"type"`
	Repo            string            `yaml:"repo"`
	StartingCommit  string            `yaml:"starting_commit"`
	Prompt          string            `yaml:"prompt"`
	Prompts         []string          `yaml:"prompts"` // for type: sequential
	SuccessCriteria []Criterion       `yaml:"success_criteria"`
	QualityRubric   []RubricDimension `yaml:"quality_rubric"`
}

// Criterion represents a success criterion with typed fields
type Criterion struct {
	Type     string   `yaml:"type"`
	Paths    []string `yaml:"paths"`
	Command  string   `yaml:"command"`
	Contains []string `yaml:"contains"`
}

// RubricDimension represents a quality rubric dimension
type RubricDimension struct {
	Dimension string `yaml:"dimension"`
	Prompt    string `yaml:"prompt"`
}

// LoadTask loads a task definition from a YAML file
func LoadTask(filename string) (*Task, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to read file %s: %w", filename, err)
	}

	var task Task
	if err := yaml.Unmarshal(data, &task); err != nil {
		return nil, fmt.Errorf("failed to parse YAML: %w", err)
	}

	// Set default type if not specified
	if task.Type == "" {
		if len(task.Prompts) > 0 {
			task.Type = "sequential"
		} else {
			task.Type = "single_shot"
		}
	}

	// Validate required fields
	if task.ID == "" {
		return nil, fmt.Errorf("task id is required")
	}

	switch task.Type {
	case "sequential":
		if len(task.Prompts) < 2 {
			return nil, fmt.Errorf("sequential task requires at least 2 prompts")
		}
	default:
		if task.Prompt == "" {
			return nil, fmt.Errorf("prompt is required for single_shot tasks")
		}
	}

	return &task, nil
}
