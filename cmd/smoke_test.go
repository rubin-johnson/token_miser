package cmd

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func buildBinary(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	bin := filepath.Join(dir, "token-miser")
	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	out, err := exec.Command("go", "build", "-o", bin, "./token-miser").CombinedOutput()
	if err != nil {
		t.Fatalf("build failed: %v\n%s", err, out)
	}
	_ = wd
	return bin
}

func TestHelp(t *testing.T) {
	bin := buildBinary(t)
	out, err := exec.Command(bin, "--help").CombinedOutput()
	if err != nil {
		t.Fatalf("--help failed: %v\n%s", err, out)
	}
	for _, sub := range []string{"run", "compare", "history", "tasks"} {
		if !strings.Contains(string(out), sub) {
			t.Errorf("--help output missing %q: %s", sub, out)
		}
	}
}

func TestTasksSubcommand(t *testing.T) {
	bin := buildBinary(t)

	// Locate the tasks directory relative to the project root
	wd, _ := os.Getwd()
	tasksDir := filepath.Join(filepath.Dir(wd), "tasks")
	if _, err := os.Stat(tasksDir); os.IsNotExist(err) {
		t.Skip("tasks directory not found, skipping")
	}

	out, err := exec.Command(bin, "tasks", "--dir", tasksDir).CombinedOutput()
	if err != nil {
		t.Fatalf("tasks --dir failed: %v\n%s", err, out)
	}
	if !strings.Contains(string(out), "synth-001") {
		t.Errorf("tasks output missing synth-001: %s", out)
	}
}
