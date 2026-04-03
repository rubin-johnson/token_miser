package cli

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
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
	_ = ctx
	if len(args) < 1 {
		return errors.New("usage: token-miser show <run-id>")
	}
	runID, err := strconv.Atoi(args[0])
	if err != nil || runID <= 0 {
		return fmt.Errorf("invalid run id: %q", args[0])
	}

	if err := db.InitDB(dbPath()); err != nil {
		return err
	}
	conn := db.Conn()
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
	qRun := `
SELECT task_id, arm, started_at, wall_seconds, input_tokens, output_tokens,
       total_cost_usd, criteria_pass, criteria_total, quality_scores, result
FROM runs
WHERE id = ?`
	if err := conn.QueryRowContext(context.Background(), qRun, runID).Scan(
		&taskID, &arm, &startedAt, &wallSeconds, &inputTokens, &outputTokens,
		&totalCostUSD, &criteriaPass, &criteriaTotal, &qJSON, &resultText,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return fmt.Errorf("run %d not found", runID)
		}
		return err
	}

	rows, err := conn.QueryContext(context.Background(), `
SELECT criterion_type, passed, COALESCE(detail, '')
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

	fmt.Printf("Run #%d — %s / %s\n", runID, taskID, arm)
	fmt.Printf("  Started:     %s\n", startedAt.Format("2006-01-02 15:04:05"))
	fmt.Printf("  Wall time:   %.1fs\n", wallSeconds)
	fmt.Printf("  Input:       %,d tokens\n", inputTokens)
	fmt.Printf("  Output:      %,d tokens\n", outputTokens)
	fmt.Printf("  Cost:        $%.3f\n", totalCostUSD)
	fmt.Printf("  Criteria:    %d/%d passed\n", criteriaPass, criteriaTotal)

	if len(crits) > 0 {
		for _, c := range crits {
			mark := "✗"
			if c.Passed {
				mark = "✓"
			}
			line := fmt.Sprintf("  %s %s", mark, c.Type)
			if c.Detail != "" {
				line += fmt.Sprintf("  (%s)", c.Detail)
			}
			fmt.Println(line)
		}
	}

	if len(qs) > 0 {
		fmt.Println("  Quality:")
		tw := tabwriter.NewWriter(os.Stdout, 0, 4, 2, ' ', 0)
		for k, v := range qs {
			fmt.Fprintf(tw, "    %s:\t%.0f\n", k, v)
		}
		_ = tw.Flush()
	}

	if resultText.Valid && strings.TrimSpace(resultText.String) != "" {
		fmt.Println("  Output:")
		fmt.Println("    " + strings.ReplaceAll(resultText.String, "\n", "\n    "))
	}

	return nil
}

func dbPath() string {
	home, _ := os.UserHomeDir()
	if home == "" {
		return "results.db"
	}
	return filepath.Join(home, ".token_miser", "results.db")
}
