package task

import (
	"fmt"
	"os"
	"strings"

	"gopkg.in/yaml.v3"
)

type Criterion struct {
	Type     string   `yaml:"type"`
	Paths    []string `yaml:"paths"`
	Command  string   `yaml:"command"`
	Contains []string `yaml:"contains"`
}

type RubricDimension struct {
	Dimension string `yaml:"dimension"`
	Prompt    string `yaml:"prompt"`
}

type Task struct {
	ID              string            `yaml:"id"`
	Name            string            `yaml:"name"`
	Type            string            `yaml:"type"`
	Repo            string            `yaml:"repo"`
	StartingCommit  string            `yaml:"starting_commit"`
	Prompt          string            `yaml:"prompt"`
	SuccessCriteria []Criterion       `yaml:"success_criteria"`
	QualityRubric   []RubricDimension `yaml:"quality_rubric"`
}

func LoadTask(path string) (*Task, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read task file: %w", err)
	}

	var t Task
	if err := yaml.Unmarshal(data, &t); err != nil {
		return nil, fmt.Errorf("parse task YAML: %w", err)
	}

	if t.Type == "" {
		t.Type = "single_shot"
	}

	var missing []string
	if t.ID == "" {
		missing = append(missing, "id")
	}
	if t.Repo == "" {
		missing = append(missing, "repo")
	}
	if t.StartingCommit == "" {
		missing = append(missing, "starting_commit")
	}
	if t.Prompt == "" {
		missing = append(missing, "prompt")
	}
	if len(missing) > 0 {
		return nil, fmt.Errorf("task missing required fields: %s", strings.Join(missing, ", "))
	}

	return &t, nil
}
