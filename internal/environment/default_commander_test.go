package environment

import (
	"strings"
	"testing"
)

func TestDefaultCommanderRun(t *testing.T) {
	c := NewDefaultCommander()
	err := c.Run("echo", []string{"hi"})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestDefaultCommanderRunWithOutput(t *testing.T) {
	c := NewDefaultCommander()
	out, err := c.RunWithOutput("echo", []string{"hello"})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if !strings.Contains(out, "hello") {
		t.Fatalf("expected 'hello' in output, got %q", out)
	}
}
