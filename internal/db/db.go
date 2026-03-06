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

const schema = `
CREATE TABLE IF NOT EXISTS runs (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	task_id TEXT NOT NULL,
	arm TEXT NOT NULL,
	loadout_name TEXT,
	model TEXT,
	started_at TEXT,
	wall_seconds REAL,
	input_tokens INTEGER,
	output_tokens INTEGER,
	cache_read_tokens INTEGER,
	cache_write_tokens INTEGER,
	total_cost_usd REAL,
	exit_code INTEGER,
	criteria_pass INTEGER,
	criteria_total INTEGER,
	quality_scores TEXT
)`

type Run struct {
	ID              int64
	TaskID          string
	Arm             string
	LoadoutName     string
	Model           string
	StartedAt       string
	WallSeconds     float64
	InputTokens     int
	OutputTokens    int
	CacheReadTokens int
	CacheWriteTokens int
	TotalCostUSD    float64
	ExitCode        int
	CriteriaPass    int
	CriteriaTotal   int
	QualityScores   string
}

func DefaultDBPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("get user home dir: %w", err)
	}
	return filepath.Join(home, ".token_miser", "results.db"), nil
}

func InitDB(path string) (*sql.DB, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return nil, fmt.Errorf("create db dir: %w", err)
	}

	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}

	return db, nil
}

func StoreRun(db *sql.DB, run *Run) (int64, error) {
	if run.StartedAt == "" {
		run.StartedAt = time.Now().UTC().Format(time.RFC3339)
	}

	res, err := db.Exec(`INSERT INTO runs
		(task_id, arm, loadout_name, model, started_at, wall_seconds,
		 input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
		 total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores)
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		run.TaskID, run.Arm, run.LoadoutName, run.Model, run.StartedAt,
		run.WallSeconds, run.InputTokens, run.OutputTokens,
		run.CacheReadTokens, run.CacheWriteTokens, run.TotalCostUSD,
		run.ExitCode, run.CriteriaPass, run.CriteriaTotal, run.QualityScores,
	)
	if err != nil {
		return 0, fmt.Errorf("insert run: %w", err)
	}

	return res.LastInsertId()
}

func GetRuns(db *sql.DB, taskID string) ([]*Run, error) {
	query := `SELECT id, task_id, arm, loadout_name, model, started_at,
		wall_seconds, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
		total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores
		FROM runs`
	args := []any{}
	if taskID != "" {
		query += " WHERE task_id = ?"
		args = append(args, taskID)
	}
	query += " ORDER BY id"

	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("query runs: %w", err)
	}
	defer rows.Close()

	var runs []*Run
	for rows.Next() {
		var r Run
		if err := rows.Scan(&r.ID, &r.TaskID, &r.Arm, &r.LoadoutName, &r.Model,
			&r.StartedAt, &r.WallSeconds, &r.InputTokens, &r.OutputTokens,
			&r.CacheReadTokens, &r.CacheWriteTokens, &r.TotalCostUSD,
			&r.ExitCode, &r.CriteriaPass, &r.CriteriaTotal, &r.QualityScores); err != nil {
			return nil, fmt.Errorf("scan run: %w", err)
		}
		runs = append(runs, &r)
	}
	return runs, rows.Err()
}

func MarshalQualityScores(scores any) (string, error) {
	data, err := json.Marshal(scores)
	if err != nil {
		return "", fmt.Errorf("marshal quality scores: %w", err)
	}
	return string(data), nil
}
