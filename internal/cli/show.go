package cli

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/rubin-johnson/token_miser/internal/db"
)

type qualityScores map[string]float64

type criterionRow struct {
	Type   string
	Passed bool
	Detail string
}

func showCommand(ctx context.Context, args []string) error {
	if len(args) < 1 {
		return errors.New("usage: token-miser show <run-id>")
	}

	runID, err := strconv.Atoi(args[0])
	if err != nil || runID <= 0 {
		return fmt.Errorf("invalid run id: %q", args[0])
	}

	dbo, err := db.InitDB(dbPath())
	if err != nil {
		return err
	}
	defer func() { _ = dbo.Close() }()

	conn := dbo.Conn()
	if conn == nil {
		return errors.New("db connection not initialized")
	}

	var (
		taskID        string
		arm           string
		startedAt     time.Time
		wallSeconds   float64
		inputTokens   int
		outputTokens  int
		totalCostUSD  float64
		criteriaPass  int
		criteriaTotal int
		qJSON         sql.NullString
		resultText    sql.NullString
	)

	const qRun = `
SELECT
  task_id,
  arm,
  started_at,
  COALESCE(wall_seconds, 0),
  input_tokens,
  output_tokens,
  COALESCE(total_cost_usd, 0),
  COALESCE(criteria_pass, 0),
  COALESCE(criteria_total, 0),
  quality_scores,
  result
FROM runs
WHERE id = ?`

	if err := conn.QueryRowContext(
		ctx, qRun, runID,
	).Scan(
		&taskID,
		&arm,
		&startedAt,
		&wallSeconds,
		&inputTokens,
		&outputTokens,
		&totalCostUSD,
		&criteriaPass,
		&criteriaTotal,
		&qJSON,
		&resultText,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return fmt.Errorf("run %d not found", runID)
		}
		return err
	}

	rows, err := conn.QueryContext(ctx, `
SELECT
  criterion_type,
  passed,
  COALESCE(detail, '')
FROM criterion_results
WHERE run_id = ?
ORDER BY id ASC`, runID)
	if err != nil {
		return err
	}
	defer rows.Close()

	var crits []criterionRow
	for rows.Next() {
		var t string
		var pInt int
		var d string
		if err := rows.Scan(&t, &pInt, &d); err != nil {
			return err
		}
		crits = append(crits, criterionRow{
			Type:   t,
			Passed: pInt == 1,
			Detail: d,
		})
	}
	if err := rows.Err(); err != nil {
		return err
	}

	qs := qualityScores{}
	if qJSON.Valid && strings.TrimSpace(qJSON.String) != "" {
		_ = json.Unmarshal([]byte(qJSON.String), &qs)
	}

	w := tabwriter.NewWriter(os.Stdout, 2, 4, 2, ' ', 0)
	fmt.Fprintf(w, "Run:\t%d\n", runID)
	fmt.Fprintf(w, "Task:\t%s\n", taskID)
	fmt.Fprintf(w, "Arm:\t%s\n", arm)
	fmt.Fprintf(w, "Started:\t%s\n", startedAt.Format(time.RFC3339))
	fmt.Fprintf(w, "Wall Time:\t%.2fs\n", wallSeconds)
	fmt.Fprintf(w, "Tokens (input/output):\t%d / %d\n", inputTokens, outputTokens)
	fmt.Fprintf(w, "Cost:\t$%.6f\n", totalCostUSD)
	fmt.Fprintf(w, "Criteria:\t%d/%d passed\n", criteriaPass, criteriaTotal)
	_ = w.Flush()

	if len(crits) > 0 {
		fmt.Println()
		fmt.Println("Criteria details:")
		for _, c := range crits {
			mark := "✗"
			if c.Passed {
				mark = "✓"
			}
			if strings.TrimSpace(c.Detail) == "" {
				fmt.Printf("- [%s] %s\n", mark, c.Type)
			} else {
				fmt.Printf("- [%s] %s: %s\n", mark, c.Type, c.Detail)
			}
		}
	}

	if len(qs) > 0 {
		fmt.Println()
		fmt.Println("Quality scores:")
		for k, v := range qs {
			fmt.Printf("- %s: %.3f\n", k, v)
		}
	}

	if resultText.Valid && strings.TrimSpace(resultText.String) != "" {
		fmt.Println()
		fmt.Println("Claude output:")
		fmt.Println(strings.TrimSpace(resultText.String))
	}

	return nil
}
