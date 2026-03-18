package db_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/db"
)

func TestDB_Conn_ReturnsNonNil(t *testing.T) {
	dir := t.TempDir()
	dbFile := filepath.Join(dir, "test.db")

	d, err := db.InitDB(dbFile)
	if err != nil {
		t.Fatalf("InitDB failed: %v", err)
	}
	defer os.Remove(dbFile)

	conn := d.Conn()
	if conn == nil {
		t.Fatal("expected non-nil *sql.DB from Conn(), got nil")
	}
}

func TestDB_Conn_IsPingable(t *testing.T) {
	dir := t.TempDir()
	dbFile := filepath.Join(dir, "test.db")

	d, err := db.InitDB(dbFile)
	if err != nil {
		t.Fatalf("InitDB failed: %v", err)
	}
	defer os.Remove(dbFile)

	conn := d.Conn()
	if err := conn.Ping(); err != nil {
		t.Fatalf("expected Conn() to be pingable, got error: %v", err)
	}
}
