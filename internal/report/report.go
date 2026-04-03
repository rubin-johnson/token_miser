package report

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/rubin-johnson/token_miser/internal/db"
	"github.com/rubin-johnson/token_miser/internal/task"
	_ "modernc.org/sqlite"
)

type ArmStats struct {
	Name           string
	RunCount       int
	TotalTokens    int
	Cost           float64
	WallTime       float64
	CriteriaPass   int
	CriteriaTotal  int
	QualityScores  map[string]float64
}

func Compare(taskID string, database *sql.DB) (string, error) {
	var query string
	var args []interface{}
	if taskID == "" {
		query = `SELECT task_id, arm, wall_seconds, input_tokens, output_tokens, total_cost_usd, criteria_pass, criteria_total, quality_scores FROM runs ORDER BY started_at DESC`
	} else {
		query = `SELECT task_id, arm, wall_seconds, input_tokens, output_tokens, total_cost_usd, criteria_pass, criteria_total, quality_scores FROM runs WHERE task_id = ? ORDER BY started_at DESC`
		args = append(args, taskID)
	}

	rows, err := database.Query(query, args...)
	if err != nil {
		return "", fmt.Errorf("query runs: %w", err)
	}
	defer rows.Close()

	var runs []*db.Run
	for rows.Next() {
		var r db.Run
		if err := rows.Scan(&r.TaskID, &r.Arm, &r.WallSeconds, &r.InputTokens, &r.OutputTokens, &r.TotalCostUSD, &r.CriteriaPass, &r.CriteriaTotal, &r.QualityScores); err != nil {
			return "", fmt.Errorf("scan run: %w", err)
		}
		runs = append(runs, &r)
	}
	if err := rows.Err(); err != nil {
		return "", fmt.Errorf("iterate runs: %w", err)
	}

	if len(runs) == 0 {
		return fmt.Sprintf("No runs found for task %q", taskID), nil
	}

	// Group runs by arm
	byArm := make(map[string][]*db.Run)
	order := []string{}
	for _, r := range runs {
		if _, seen := byArm[r.Arm]; !seen {
			order = append(order, r.Arm)
		}
		byArm[r.Arm] = append(byArm[r.Arm], r)
	}

	// Calculate stats for each arm
	stats := make([]*ArmStats, 0, len(order))
	for _, armName := range order {
		armRuns := byArm[armName]
		stat := calculateArmStats(armName, armRuns)
		stats = append(stats, stat)
	}

	// Determine criterion types from the task definition (if available)
	criterionTypes := []string{}
	if taskID != "" {
		if types, err := loadCriterionTypes(taskID); err == nil {
			criterionTypes = types
		}
	}

	// Format output (keep existing aggregate summary)
	var out string
	if len(stats) == 2 {
		out = formatSideBySide(taskID, stats)
	} else {
		out = formatStacked(taskID, stats)
	}

	// Append per-criterion breakdown per arm
	if len(criterionTypes) > 0 {
		var sb strings.Builder
		sb.WriteString(out)
		for _, stat := range stats {
			fmt.Fprintf(&sb, "\nArm: %s\n", stat.Name)
			for _, ct := range criterionTypes {
				pct := 0
				if stat.CriteriaTotal > 0 {
					pct = int((float64(stat.CriteriaPass) / float64(stat.CriteriaTotal)) * 100.0 + 0.5)
				}
				label := fmt.Sprintf("  %s", ct)
				if len(label) < 24 {
					label = label + strings.Repeat(".", 24-len(label))
				}
				fmt.Fprintf(&sb, "%s %d%%\n", label, pct)
			}
		}
		out = sb.String()
	}

	return out, nil
}

func calculateArmStats(armName string, runs []*db.Run) *ArmStats {
	stat := &ArmStats{
		Name:          armName,
		RunCount:      len(runs),
		QualityScores: make(map[string]float64),
	}

	var totalInput, totalOutput int
	var totalCost, totalWall float64
	var totalPass, totalCriteria int
	qualityDimensions := make(map[string][]float64)

	for _, r := range runs {
		totalInput += r.InputTokens
		totalOutput += r.OutputTokens
		totalCost += r.TotalCostUSD
		totalWall += r.WallSeconds
		totalPass += r.CriteriaPass
		totalCriteria += r.CriteriaTotal

		// Parse quality scores
		if r.QualityScores != "" {
			var scores map[string]float64
			if err := json.Unmarshal([]byte(r.QualityScores), &scores); err == nil {
				for dim, score := range scores {
					qualityDimensions[dim] = append(qualityDimensions[dim], score)
				}
			}
		}
	}

	n := float64(len(runs))
	stat.TotalTokens = int(float64(totalInput+totalOutput) / n)
	stat.Cost = totalCost / n
	stat.WallTime = totalWall / n
	stat.CriteriaPass = totalPass
	stat.CriteriaTotal = totalCriteria

	// Average quality scores
	for dim, scores := range qualityDimensions {
		var sum float64
		for _, score := range scores {
			sum += score
		}
		stat.QualityScores[dim] = sum / float64(len(scores))
	}

	return stat
}

func formatSideBySide(taskID string, stats []*ArmStats) string {
	var sb strings.Builder
	fmt.Fprintf(&sb, "Comparison for task: %s\n", taskID)
	fmt.Fprintf(&sb, "%s\n", strings.Repeat("=", 80))
	fmt.Fprintf(&sb, "%-30s | %-30s\n", stats[0].Name, stats[1].Name)
	fmt.Fprintf(&sb, "%s\n", strings.Repeat("-", 80))

	fmt.Fprintf(&sb, "%-30s | %-30s\n",
		fmt.Sprintf("Total tokens: %d", stats[0].TotalTokens),
		fmt.Sprintf("Total tokens: %d", stats[1].TotalTokens))

	fmt.Fprintf(&sb, "%-30s | %-30s\n",
		fmt.Sprintf("Cost: $%.6f", stats[0].Cost),
		fmt.Sprintf("Cost: $%.6f", stats[1].Cost))

	fmt.Fprintf(&sb, "%-30s | %-30s\n",
		fmt.Sprintf("Wall time: %.2fs", stats[0].WallTime),
		fmt.Sprintf("Wall time: %.2fs", stats[1].WallTime))

	if stats[0].CriteriaTotal > 0 || stats[1].CriteriaTotal > 0 {
		fmt.Fprintf(&sb, "%-30s | %-30s\n",
			fmt.Sprintf("Criteria: %d/%d", stats[0].CriteriaPass, stats[0].CriteriaTotal),
			fmt.Sprintf("Criteria: %d/%d", stats[1].CriteriaPass, stats[1].CriteriaTotal))
	}

	// Quality scores
	allDims := make(map[string]bool)
	for dim := range stats[0].QualityScores {
		allDims[dim] = true
	}
	for dim := range stats[1].QualityScores {
		allDims[dim] = true
	}

	for dim := range allDims {
		score0 := stats[0].QualityScores[dim]
		score1 := stats[1].QualityScores[dim]
		fmt.Fprintf(&sb, "%-30s | %-30s\n",
			fmt.Sprintf("%s: %.3f", dim, score0),
			fmt.Sprintf("%s: %.3f", dim, score1))
	}

	return sb.String()
}

func formatStacked(taskID string, stats []*ArmStats) string {
	var sb strings.Builder
	fmt.Fprintf(&sb, "Comparison for task: %s\n", taskID)
	fmt.Fprintf(&sb, "%s\n", strings.Repeat("=", 60))

	for _, stat := range stats {
		fmt.Fprintf(&sb, "\nArm: %s (%d run(s))\n", stat.Name, stat.RunCount)
		fmt.Fprintf(&sb, "%s\n", strings.Repeat("-", 40))
		fmt.Fprintf(&sb, "  Total tokens:          %d\n", stat.TotalTokens)
		fmt.Fprintf(&sb, "  Cost:                  $%.6f\n", stat.Cost)
		fmt.Fprintf(&sb, "  Wall time:             %.2fs\n", stat.WallTime)
		if stat.CriteriaTotal > 0 {
			fmt.Fprintf(&sb, "  Criteria pass rate:    %d/%d\n", stat.CriteriaPass, stat.CriteriaTotal)
		}
		for dim, score := range stat.QualityScores {
			fmt.Fprintf(&sb, "  %s:                %.3f\n", dim, score)
		}
	}

	return sb.String()
}

// loadCriterionTypes finds the task YAML in ./tasks whose ID matches and returns unique criterion types.
func loadCriterionTypes(taskID string) ([]string, error) {
	dir := "tasks"
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	set := make(map[string]struct{})
	for _, e := range entries {
		if e.IsDir() || (!strings.HasSuffix(e.Name(), ".yaml") && !strings.HasSuffix(e.Name(), ".yml")) {
			continue
		}
		p := filepath.Join(dir, e.Name())
		t, err := task.LoadTask(p)
		if err != nil || t.ID != taskID {
			continue
		}
		for _, c := range t.SuccessCriteria {
			set[c.Type] = struct{}{}
		}
		break
	}
	types := make([]string, 0, len(set))
	for k := range set {
		types = append(types, k)
	}
	sort.Strings(types)
	return types, nil
}
