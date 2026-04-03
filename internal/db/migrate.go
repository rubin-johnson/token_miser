package db

import (
	"database/sql"
	"fmt"
)

// Migrate ensures the schema contains new observability columns/tables.
// Idempotent: safe to run multiple times.
func Migrate(conn *sql.DB) error {
	// Add runs.result TEXT if missing
	if _, err := conn.Exec(`ALTER TABLE runs ADD COLUMN result TEXT`); err != nil {
		// Ignore if column already exists
		if !isAlreadyExistsErr(err) {
			return fmt.Errorf("add runs.result: %w", err)
		}
	}
	// Ensure wall_seconds column exists for older DBs (SQLite ALTER ADD COLUMN is idempotent by error)
	if _, err := conn.Exec(`ALTER TABLE runs ADD COLUMN wall_seconds REAL NOT NULL DEFAULT 0`); err != nil {
		if !isAlreadyExistsErr(err) {
			return fmt.Errorf("add runs.wall_seconds: %w", err)
		}
	}
	// Create criterion_results table if not exists
	_, err := conn.Exec(`CREATE TABLE IF NOT EXISTS criterion_results (
		id INTEGER PRIMARY KEY,
		run_id INTEGER REFERENCES runs(id),
		criterion_type TEXT,
		passed INTEGER,
		detail TEXT
	)`)
	if err != nil {
		return fmt.Errorf("create criterion_results: %w", err)
	}
	return nil
}

// SQLite emits an error string containing "duplicate column name" when adding existing columns.
func isAlreadyExistsErr(err error) bool {
	if err == nil {
		return false
	}
	s := err.Error()
	return containsAny(s, []string{"duplicate column name", "already exists"})
}

func containsAny(s string, subs []string) bool {
	for _, sub := range subs {
		if contains(s, sub) {
			return true
		}
	}
	return false
}

func contains(s, sub string) bool { return len(sub) > 0 && (len(s) >= len(sub)) && (indexOf(s, sub) >= 0) }

func indexOf(s, sub string) int {
	// naive substring search; fine for small error messages
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}
