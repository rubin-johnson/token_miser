package report

import (
	"fmt"
	"strings"

	"database/sql"

	"github.com/rubin-johnson/token_miser/internal/db"
)

func Compare(taskID string, database *sql.DB) (string, error) {
	runs, err := db.GetRuns(database, taskID)
	if err != nil {
		return "", fmt.Errorf("get runs: %w", err)
	}
	if len(runs) == 0 {
		return fmt.Sprintf("No runs found for task %q", taskID), nil
	}

	byArm := make(map[string][]*db.Run)
	order := []string{}
	for _, r := range runs {
		if _, seen := byArm[r.Arm]; !seen {
			order = append(order, r.Arm)
		}
		byArm[r.Arm] = append(byArm[r.Arm], r)
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "Comparison for task: %s\n", taskID)
	fmt.Fprintf(&sb, "%s\n", strings.Repeat("=", 60))

	for _, armName := range order {
		armRuns := byArm[armName]
		fmt.Fprintf(&sb, "\nArm: %s (%d run(s))\n", armName, len(armRuns))
		fmt.Fprintf(&sb, "%s\n", strings.Repeat("-", 40))

		var totalInput, totalOutput int
		var totalCost, totalWall float64
		var totalPass, totalCriteria int

		for _, r := range armRuns {
			totalInput += r.InputTokens
			totalOutput += r.OutputTokens
			totalCost += r.TotalCostUSD
			totalWall += r.WallSeconds
			totalPass += r.CriteriaPass
			totalCriteria += r.CriteriaTotal
		}

		n := len(armRuns)
		fmt.Fprintf(&sb, "  input tokens (avg):    %d\n", totalInput/n)
		fmt.Fprintf(&sb, "  output tokens (avg):   %d\n", totalOutput/n)
		fmt.Fprintf(&sb, "  cost USD (avg):        $%.6f\n", totalCost/float64(n))
		fmt.Fprintf(&sb, "  wall seconds (avg):    %.2f\n", totalWall/float64(n))
		if totalCriteria > 0 {
			fmt.Fprintf(&sb, "  criteria pass rate:    %d/%d\n", totalPass, totalCriteria)
		}
	}

	return sb.String(), nil
}
