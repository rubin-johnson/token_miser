package db

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

// Run represents a single experimental run stored in the database
type Run struct {
	ID               int64     `json:"id"`
	TaskID           string    `json:"task_id"`
	Arm              string    `json:"arm"`
	LoadoutName      string    `json:"loadout_name"`
	Model            string    `json:"model"`
	StartedAt        time.Time `json:"started_at"`
	WallSeconds      float64   `json:"wall_seconds"`
	InputTokens      int       `json:"input_tokens"`
	OutputTokens     int       `json:"output_tokens"`
	CacheReadTokens  int       `json:"cache_read_tokens"`
	CacheWriteTokens int       `json:"cache_write_tokens"`
	TotalCostUSD     float64   `json:"total_cost_usd"`
	ExitCode         int       `json:"exit_code"`
	CriteriaPass     int       `json:"criteria_pass"`
	CriteriaTotal    int       `json:"criteria_total"`
	QualityScores    string    `json:"quality_scores"`
	Result           string    `json:"result"`
}

// DB wraps the SQLite database connection
type DB struct {
	conn *sql.DB
}

// InitDB initializes the database connection and creates tables
func InitDB(dbPath string) (*DB, error) {
	// Create directory if it doesn't exist
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create directory %s: %w", dir, err)
	}

	// Open database connection
	conn, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	db := &DB{conn: conn}

	// Create tables
	if err := db.createTables(); err != nil {
		return nil, fmt.Errorf("failed to create tables: %w", err)
	}

	return db, nil
}

// createTables creates the runs table with all required columns
func (db *DB) createTables() error {
	query := `
	CREATE TABLE IF NOT EXISTS runs (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		task_id TEXT NOT NULL,
		arm TEXT NOT NULL,
		loadout_name TEXT NOT NULL DEFAULT '',
		model TEXT NOT NULL DEFAULT '',
		started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		wall_seconds REAL NOT NULL DEFAULT 0,
		input_tokens INTEGER NOT NULL DEFAULT 0,
		output_tokens INTEGER NOT NULL DEFAULT 0,
		cache_read_tokens INTEGER NOT NULL DEFAULT 0,
		cache_write_tokens INTEGER NOT NULL DEFAULT 0,
		total_cost_usd REAL NOT NULL DEFAULT 0,
		exit_code INTEGER NOT NULL DEFAULT 0,
		criteria_pass INTEGER NOT NULL DEFAULT 0,
		criteria_total INTEGER NOT NULL DEFAULT 0,
		quality_scores TEXT NOT NULL DEFAULT '',
		result TEXT NOT NULL DEFAULT ''
	);
	`

	if _, err := db.conn.Exec(query); err != nil {
		return err
	}
	// Ensure result column exists on pre-existing databases (idempotent)
	_, _ = db.conn.Exec(`ALTER TABLE runs ADD COLUMN result TEXT NOT NULL DEFAULT ''`)

	// Ensure criterion_results exists (idempotent)
	crit := `
	CREATE TABLE IF NOT EXISTS criterion_results (
		id INTEGER PRIMARY KEY,
		run_id INTEGER REFERENCES runs(id),
		criterion_type TEXT,
		passed INTEGER,
		detail TEXT
	);
	`
	_, err := db.conn.Exec(crit)
	return err
}

// StoreRun inserts a run into the database and returns its ID
func (db *DB) StoreRun(run *Run) (int64, error) {
	query := `
	INSERT INTO runs (task_id, arm, loadout_name, model, started_at, wall_seconds,
		input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
		total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores, result)
	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	result, err := db.conn.Exec(query,
		run.TaskID, run.Arm, run.LoadoutName, run.Model, time.Now(),
		run.WallSeconds, run.InputTokens, run.OutputTokens,
		run.CacheReadTokens, run.CacheWriteTokens, run.TotalCostUSD,
		run.ExitCode, run.CriteriaPass, run.CriteriaTotal, run.QualityScores, run.Result)
	if err != nil {
		return 0, fmt.Errorf("failed to insert run: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return 0, fmt.Errorf("failed to get last insert ID: %w", err)
	}

	return id, nil
}

// GetRuns retrieves runs from the database, optionally filtered by task ID
func (db *DB) GetRuns(taskID string) ([]Run, error) {
	var query string
	var args []interface{}

	if taskID == "" {
		query = `SELECT id, task_id, arm, loadout_name, model, started_at, wall_seconds,
			input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
			total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores, result
			FROM runs ORDER BY started_at DESC`
	} else {
		query = `SELECT id, task_id, arm, loadout_name, model, started_at, wall_seconds,
			input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
			total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores, result
			FROM runs WHERE task_id = ? ORDER BY started_at DESC`
		args = append(args, taskID)
	}

	rows, err := db.conn.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query runs: %w", err)
	}
	defer rows.Close()

	var runs []Run
	for rows.Next() {
		var run Run
		err := rows.Scan(&run.ID, &run.TaskID, &run.Arm, &run.LoadoutName, &run.Model,
			&run.StartedAt, &run.WallSeconds, &run.InputTokens, &run.OutputTokens,
			&run.CacheReadTokens, &run.CacheWriteTokens, &run.TotalCostUSD,
			&run.ExitCode, &run.CriteriaPass, &run.CriteriaTotal, &run.QualityScores, &run.Result)
		if err != nil {
			return nil, fmt.Errorf("failed to scan run: %w", err)
		}
		runs = append(runs, run)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return runs, nil
}

// Conn returns the underlying *sql.DB connection
func (db *DB) Conn() *sql.DB {
	return db.conn
}

// Close closes the database connection
func (db *DB) Close() error {
	return db.conn.Close()
}
