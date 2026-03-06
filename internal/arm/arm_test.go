package arm

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseArm_Vanilla(t *testing.T) {
	a, err := ParseArm("vanilla")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if a.Name != "vanilla" || a.LoadoutPath != "" {
		t.Errorf("got %+v, want {Name:vanilla LoadoutPath:}", a)
	}
}

func TestParseArm_ExistingDir(t *testing.T) {
	dir := t.TempDir()
	a, err := ParseArm(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if a.LoadoutPath != dir {
		t.Errorf("LoadoutPath: got %q, want %q", a.LoadoutPath, dir)
	}
	if a.Name != filepath.Base(dir) {
		t.Errorf("Name: got %q, want %q", a.Name, filepath.Base(dir))
	}
}

func TestParseArm_NonexistentPath(t *testing.T) {
	_, err := ParseArm("/nonexistent-path-that-does-not-exist-12345")
	if err == nil {
		t.Fatal("expected error for nonexistent path, got nil")
	}
}

func TestParseArm_FileNotDir(t *testing.T) {
	f, err := os.CreateTemp("", "arm-test-*.txt")
	if err != nil {
		t.Fatal(err)
	}
	f.Close()
	defer os.Remove(f.Name())

	_, err = ParseArm(f.Name())
	if err == nil {
		t.Fatal("expected error for file path, got nil")
	}
}
