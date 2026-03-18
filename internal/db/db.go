package db

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

// Run represents a single experimental run stored in the database
type Run struct {
	ID            int64     `json:"id"`
	TaskName      string    `json:"task_name"`
	ArmName       string    `json:"arm_name"`
	PromptTokens  int       `json:"prompt_tokens"`
	OutputTokens  int       `json:"output_tokens"`
	TotalTokens   int       `json:"total_tokens"`
	Cost          float64   `json:"cost"`
	QualityScores string    `json:"quality_scores"` // JSON string
	Timestamp     time.Time `json:"timestamp"`
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
		task_name TEXT NOT NULL,
		arm_name TEXT NOT NULL,
		prompt_tokens INTEGER NOT NULL,
		output_tokens INTEGER NOT NULL,
		total_tokens INTEGER NOT NULL,
		cost REAL NOT NULL,
		quality_scores TEXT NOT NULL,
		timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
	);
	`

	_, err := db.conn.Exec(query)
	return err
}

// StoreRun inserts a run into the database and returns its ID
func (db *DB) StoreRun(taskName, armName string, promptTokens, outputTokens, totalTokens int, cost float64, qualityScores map[string]interface{}) (int64, error) {
	// Convert quality scores to JSON string
	qualityJSON, err := json.Marshal(qualityScores)
	if err != nil {
		return 0, fmt.Errorf("failed to marshal quality scores: %w", err)
	}

	query := `
	INSERT INTO runs (task_name, arm_name, prompt_tokens, output_tokens, total_tokens, cost, quality_scores, timestamp)
	VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`

	result, err := db.conn.Exec(query, taskName, armName, promptTokens, outputTokens, totalTokens, cost, string(qualityJSON), time.Now())
	if err != nil {
		return 0, fmt.Errorf("failed to insert run: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return 0, fmt.Errorf("failed to get last insert ID: %w", err)
	}

	return id, nil
}

// GetRuns retrieves runs from the database, optionally filtered by task name
func (db *DB) GetRuns(taskName string) ([]Run, error) {
	var query string
	var args []interface{}

	if taskName == "" {
		query = "SELECT id, task_name, arm_name, prompt_tokens, output_tokens, total_tokens, cost, quality_scores, timestamp FROM runs ORDER BY timestamp DESC"
	} else {
		query = "SELECT id, task_name, arm_name, prompt_tokens, output_tokens, total_tokens, cost, quality_scores, timestamp FROM runs WHERE task_name = ? ORDER BY timestamp DESC"
		args = append(args, taskName)
	}

	rows, err := db.conn.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query runs: %w", err)
	}
	defer rows.Close()

	var runs []Run
	for rows.Next() {
		var run Run
		err := rows.Scan(&run.ID, &run.TaskName, &run.ArmName, &run.PromptTokens, &run.OutputTokens, &run.TotalTokens, &run.Cost, &run.QualityScores, &run.Timestamp)
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

// Close closes the database connection
func (db *DB) Close() error {
	return db.conn.Close()
}
