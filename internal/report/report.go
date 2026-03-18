package report

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/rubin-johnson/token_miser/internal/db"
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
	runs, err := db.GetRuns(database, taskID)
	if err != nil {
		return "", fmt.Errorf("get runs: %w", err)
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

	// Format output
	if len(stats) == 2 {
		return formatSideBySide(taskID, stats), nil
	}
	return formatStacked(taskID, stats), nil
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
