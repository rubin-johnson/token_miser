package arm

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseArm(t *testing.T) {
	t.Run("vanilla returns empty loadout path", func(t *testing.T) {
		arm, err := ParseArm("vanilla")
		if err != nil {
			t.Fatalf("expected no error, got %v", err)
		}
		if arm.Name != "vanilla" {
			t.Errorf("expected Name to be 'vanilla', got %s", arm.Name)
		}
		if arm.LoadoutPath != "" {
			t.Errorf("expected LoadoutPath to be empty, got %s", arm.LoadoutPath)
		}
	})

	t.Run("existing directory returns correct arm", func(t *testing.T) {
		// Create a temporary directory
		tempDir, err := os.MkdirTemp("", "test_arm_dir")
		if err != nil {
			t.Fatalf("failed to create temp dir: %v", err)
		}
		defer os.RemoveAll(tempDir)

		arm, err := ParseArm(tempDir)
		if err != nil {
			t.Fatalf("expected no error, got %v", err)
		}
		expectedName := filepath.Base(tempDir)
		if arm.Name != expectedName {
			t.Errorf("expected Name to be %s, got %s", expectedName, arm.Name)
		}
		if arm.LoadoutPath != tempDir {
			t.Errorf("expected LoadoutPath to be %s, got %s", tempDir, arm.LoadoutPath)
		}
	})

	t.Run("nonexistent path returns error", func(t *testing.T) {
		_, err := ParseArm("/nonexistent/path/that/does/not/exist")
		if err == nil {
			t.Fatal("expected error for nonexistent path, got nil")
		}
	})

	t.Run("file path returns error", func(t *testing.T) {
		// Create a temporary file
		tempFile, err := os.CreateTemp("", "test_arm_file")
		if err != nil {
			t.Fatalf("failed to create temp file: %v", err)
		}
		tempFile.Close()
		defer os.Remove(tempFile.Name())

		_, err = ParseArm(tempFile.Name())
		if err == nil {
			t.Fatal("expected error for file path, got nil")
		}
	})
}
