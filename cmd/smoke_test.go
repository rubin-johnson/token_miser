package main_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

const fakeClaudeScript = `#!/bin/sh
printf '{"result":"task complete","total_cost_usd":0.001,"usage":{"input_tokens":100,"output_tokens":50,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}\n'
`

const fakeLoadoutScript = `#!/bin/sh
exit 0
`

// buildBinary compiles token-miser into dir and returns the binary path.
func buildBinary(t *testing.T, dir string) string {
	t.Helper()
	binPath := filepath.Join(dir, "token-miser")
	cmd := exec.Command("go", "build", "-o", binPath, "./cmd/token-miser")
	cmd.Dir = moduleRoot(t)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("build failed: %v\n%s", err, out)
	}
	return binPath
}

// moduleRoot walks up from this file's directory to find the go.mod root.
func moduleRoot(t *testing.T) string {
	t.Helper()
	// This file is at cmd/smoke_test.go; the module root is one level up.
	dir, err := filepath.Abs(".")
	if err != nil {
		t.Fatalf("get abs dir: %v", err)
	}
	// Walk up until we find go.mod
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("could not find go.mod")
		}
		dir = parent
	}
}

// writeFakeScript creates an executable shell script at path with content.
func writeFakeScript(t *testing.T, path, content string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0755); err != nil {
		t.Fatalf("write fake script %s: %v", path, err)
	}
}

func TestSmokeRun(t *testing.T) {
	root := moduleRoot(t)

	binDir := t.TempDir()
	binPath := buildBinary(t, binDir)

	// Set up fake claude and loadout in a temp bin dir.
	fakeBinDir := t.TempDir()
	writeFakeScript(t, filepath.Join(fakeBinDir, "claude"), fakeClaudeScript)
	writeFakeScript(t, filepath.Join(fakeBinDir, "loadout"), fakeLoadoutScript)

	// DB in a temp dir so we don't pollute the user's ~/.token_miser.
	dbDir := t.TempDir()
	dbPath := filepath.Join(dbDir, "results.db")

	// Build PATH: fake bins first, then real PATH.
	origPath := os.Getenv("PATH")
	testPath := fakeBinDir + ":" + origPath

	taskPath := filepath.Join(root, "tasks", "synth-001.yaml")

	// Run token-miser run.
	runCmd := exec.Command(binPath,
		"run",
		"--task", taskPath,
		"--control", "vanilla",
		"--treatment", root,
		"--model", "sonnet",
		"--db", dbPath,
	)
	runCmd.Dir = root
	runCmd.Env = append(os.Environ(), "PATH="+testPath)

	out, err := runCmd.CombinedOutput()
	t.Logf("run output:\n%s", out)
	if err != nil {
		t.Fatalf("token-miser run failed: %v\noutput:\n%s", err, out)
	}

	// Verify DB file exists.
	if _, err := os.Stat(dbPath); err != nil {
		t.Fatalf("DB file not found at %s: %v", dbPath, err)
	}

	// Determine the treatment arm name (filepath.Base of root).
	treatmentName := filepath.Base(root)

	// Run token-miser compare.
	compareCmd := exec.Command(binPath,
		"compare",
		"--task", "synth-001",
		"--db", dbPath,
	)
	compareCmd.Dir = root
	compareCmd.Env = os.Environ()

	compareOut, err := compareCmd.CombinedOutput()
	t.Logf("compare output:\n%s", compareOut)
	if err != nil {
		t.Fatalf("token-miser compare failed: %v\noutput:\n%s", err, compareOut)
	}

	output := string(compareOut)
	if !strings.Contains(output, "vanilla") {
		t.Errorf("compare output does not contain %q", "vanilla")
	}
	if !strings.Contains(output, treatmentName) {
		t.Errorf("compare output does not contain treatment arm name %q", treatmentName)
	}
}
