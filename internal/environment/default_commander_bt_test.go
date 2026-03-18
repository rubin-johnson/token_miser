package environment_test

import (
	"strings"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/environment"
)

func TestDefaultCommander_Run_NoError(t *testing.T) {
	c := environment.NewDefaultCommander()
	err := c.Run("echo", []string{"hello"})
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
}

func TestDefaultCommander_RunWithOutput_ReturnsStdout(t *testing.T) {
	c := environment.NewDefaultCommander()
	out, err := c.RunWithOutput("echo", []string{"world"})
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if !strings.Contains(out, "world") {
		t.Fatalf("expected output to contain 'world', got: %q", out)
	}
}

func TestDefaultCommander_Run_NonexistentBinary_ReturnsError(t *testing.T) {
	c := environment.NewDefaultCommander()
	err := c.Run("__nonexistent_binary_xyz__", []string{})
	if err == nil {
		t.Fatal("expected error for nonexistent binary, got nil")
	}
}

func TestDefaultCommander_RunWithOutput_NonexistentBinary_ReturnsError(t *testing.T) {
	c := environment.NewDefaultCommander()
	_, err := c.RunWithOutput("__nonexistent_binary_xyz__", []string{})
	if err == nil {
		t.Fatal("expected error for nonexistent binary, got nil")
	}
}
