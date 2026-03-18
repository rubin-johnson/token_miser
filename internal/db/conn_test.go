package db

import (
	"path/filepath"
	"testing"
)

func TestConn_ReturnsSameConnection(t *testing.T) {
	dir := t.TempDir()
	d, err := InitDB(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatalf("InitDB: %v", err)
	}
	if d.Conn() == nil {
		t.Fatal("Conn() returned nil")
	}
	// Verify it's the same pointer as the internal conn field
	if d.Conn() != d.conn {
		t.Fatal("Conn() did not return the internal conn field")
	}
}
