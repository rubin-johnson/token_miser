package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestCompareCommand_FlagParsing(t *testing.T) {
	dir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	// Initialize empty DB so InitDB doesn't fail
	dbDir := filepath.Join(dir, ".token_miser")
	os.MkdirAll(dbDir, 0755)

	var buf bytes.Buffer
	err := compareCommand([]string{"--task", "test-task"}, &buf)
	if err != nil {
		t.Fatalf("compareCommand failed: %v", err)
	}
}
