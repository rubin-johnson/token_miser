package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDbPath_EndsWithExpectedSuffix(t *testing.T) {
	dir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	p := dbPath()
	if !strings.HasSuffix(p, filepath.Join(".token_miser", "results.db")) {
		t.Fatalf("dbPath() = %q, want suffix %q", p, filepath.Join(".token_miser", "results.db"))
	}
}
