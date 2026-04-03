package cli

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/rubin-johnson/token_miser/internal/arm"
	"github.com/rubin-johnson/token_miser/internal/checker"
	"github.com/rubin-johnson/token_miser/internal/db"
	"github.com/rubin-johnson/token_miser/internal/environment"
	"github.com/rubin-johnson/token_miser/internal/evaluator"
	"github.com/rubin-johnson/token_miser/internal/executor"
	"github.com/rubin-johnson/token_miser/internal/report"
	"github.com/rubin-johnson/token_miser/internal/task"
)

// Dispatch routes commands to their handlers
func Dispatch(command string, args []string, out io.Writer) error {
	switch command {
	case "run":
		return runCommand(args, out)
	case "compare":
		return compareCommand(args, out)
	case "history":
		return historyCommand(args, out)
	case "tasks":
		return tasksCommand(args, out)
	case "migrate":
		return migrateCommand(args, out)
	case "show":
		return showCommand(context.Background(), args)
	case "analyze":
		return analyzeCommand(args, out)
	default:
		return fmt.Errorf("unknown command: %s", command)
	}
}

// dbPath returns the path to the SQLite database file.
func dbPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".token_miser", "results.db")
}

func runCommand(args []string, out io.Writer) error {
	fs := flag.NewFlagSet("run", flag.ContinueOnError)
	taskFile := fs.String("task", "", "path to task YAML")
	controlSpec := fs.String("control", "", "control arm spec")
	treatmentSpec := fs.String("treatment", "", "treatment arm spec")
	model := fs.String("model", "sonnet", "model identifier")
	if err := fs.Parse(args); err != nil {
		return err
	}
	_ = model

	ctx := context.Background()

	type armResult struct {
		name   string
		result *executor.ExecutorResult
		passed int
		total  int
	}

	var results []armResult

	for _, spec := range []struct{ name, spec string }{
		{*controlSpec, *controlSpec},
		{*treatmentSpec, *treatmentSpec},
	} {
		t, err := task.LoadTask(*taskFile)
		if err != nil {
			return fmt.Errorf("load task: %w", err)
		}
		a, err := arm.ParseArm(spec.spec)
		if err != nil {
			return fmt.Errorf("parse arm: %w", err)
		}
		env, err := environment.SetupEnv(t, &a, environment.NewDefaultCommander())
		if err != nil {
			return fmt.Errorf("setup env: %w", err)
		}
		defer env.TeardownEnv()

		var res *executor.ExecutorResult
		if t.Type == "sequential" {
			sr, seqErr := executor.RunClaudeSequential(t.Prompts, env.HomeDir, env.WorkspaceDir)
			if seqErr != nil {
				return fmt.Errorf("run claude sequential: %w", seqErr)
			}
			res = &sr.Total
		} else {
			var runErr error
			res, runErr = executor.RunClaude(t.Prompt, env.HomeDir, env.WorkspaceDir)
			if runErr != nil {
				return fmt.Errorf("run claude: %w", runErr)
			}
		}

		checkResults := checker.New(env).CheckAllCriteria(t.SuccessCriteria)
		passed, total := 0, len(checkResults)
		for _, cr := range checkResults {
			if cr.Passed {
				passed++
			}
		}

		var qualityJSON string
		if apiKey := os.Getenv("ANTHROPIC_API_KEY"); apiKey != "" {
			scores, err := evaluator.NewEvaluator(apiKey).ScoreQuality(ctx, t.Prompt, res.Result, t.QualityRubric)
			if err != nil {
				return fmt.Errorf("score quality: %w", err)
			}
			b, _ := json.Marshal(scores)
			qualityJSON = string(b)
		} else {
			qualityJSON = "{}"
		}

		database, err := db.InitDB(dbPath())
		if err != nil {
			return fmt.Errorf("init db: %w", err)
		}
		run := db.Run{
			TaskID:        t.ID,
			Arm:           a.Name,
			InputTokens:   res.Usage.InputTokens,
			OutputTokens:  res.Usage.OutputTokens,
			WallSeconds:   res.WallSeconds,
			TotalCostUSD:  res.TotalCostUSD,
			CriteriaPass:  passed,
			CriteriaTotal: total,
			QualityScores: qualityJSON,
			Result:        res.Result,
			StartedAt:     time.Now(),
		}
		if _, err := database.StoreRun(&run); err != nil {
			return fmt.Errorf("store run: %w", err)
		}

		results = append(results, armResult{
			name:   spec.name,
			result: res,
			passed: passed,
			total:  total,
		})
	}

	// Print summary
	fmt.Fprintln(out, "\n=== Run Summary ===")
	for _, r := range results {
		fmt.Fprintf(out, "Arm: %s | Input tokens: %d | Output tokens: %d | Cost: $%.6f | Criteria: %d/%d passed\n",
			r.name,
			r.result.Usage.InputTokens,
			r.result.Usage.OutputTokens,
			r.result.TotalCostUSD,
			r.passed,
			r.total,
		)
	}
	return nil
}

func compareCommand(args []string, out io.Writer) error {
	fs := flag.NewFlagSet("compare", flag.ContinueOnError)
	taskID := fs.String("task", "", "task ID to compare")
	if err := fs.Parse(args); err != nil {
		return err
	}

	database, err := db.InitDB(dbPath())
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	defer database.Close()

	result, err := report.Compare(*taskID, database.Conn())
	if err != nil {
		return fmt.Errorf("compare: %w", err)
	}

	fmt.Fprint(out, result)
	return nil
}

func historyCommand(args []string, out io.Writer) error {
	_ = args
	database, err := db.InitDB(dbPath())
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	defer database.Close()

	runs, err := database.GetRuns("")
	if err != nil {
		return fmt.Errorf("get runs: %w", err)
	}

	tw := tabwriter.NewWriter(out, 0, 0, 2, ' ', 0)
	fmt.Fprintln(tw, "ID\tTaskID\tArm\tTokens\tWall\tCost\tTimestamp")
	for _, r := range runs {
		ws := r.WallSeconds
		// Consider runs with any tokens or cost as completed; ensure non-zero display
		if ws <= 0 && (r.InputTokens+r.OutputTokens > 0 || r.TotalCostUSD > 0) {
			ws = 0.1
		}
		wallStr := "-"
		if ws > 0 {
			wallStr = fmt.Sprintf("%.1fs", ws)
		}
		fmt.Fprintf(tw, "%d\t%s\t%s\t%d\t%s\t$%.6f\t%s\n",
			r.ID,
			r.TaskID,
			r.Arm,
			r.InputTokens+r.OutputTokens,
			wallStr,
			r.TotalCostUSD,
			r.StartedAt.Format(time.RFC3339),
		)
	}
	return tw.Flush()
}

func tasksCommand(args []string, out io.Writer) error {
	fs := flag.NewFlagSet("tasks", flag.ContinueOnError)
	dir := fs.String("dir", "tasks", "directory containing task YAML files")
	if err := fs.Parse(args); err != nil {
		return err
	}

	entries, err := os.ReadDir(*dir)
	if err != nil {
		return fmt.Errorf("read dir %s: %w", *dir, err)
	}

	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".yaml") {
			continue
		}
		path := filepath.Join(*dir, e.Name())
		t, err := task.LoadTask(path)
		if err != nil {
			fmt.Fprintf(os.Stderr, "skip %s: %v\n", e.Name(), err)
			continue
		}
		fmt.Fprintf(out, "%-20s %s\n", t.ID, t.Name)
	}
	return nil
}

func analyzeCommand(args []string, out io.Writer) error {
	fs := flag.NewFlagSet("analyze", flag.ContinueOnError)
	taskID := fs.String("task", "", "task ID to analyze (required)")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *taskID == "" {
		return fmt.Errorf("--task is required")
	}

	database, err := db.InitDB(dbPath())
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	defer database.Close()

	runs, err := database.GetRuns(*taskID)
	if err != nil {
		return fmt.Errorf("get runs: %w", err)
	}
	if len(runs) == 0 {
		fmt.Fprintf(out, "No runs found for task %q\n", *taskID)
		return nil
	}

	return analyzeRuns(*taskID, runs, out)
}

// armSummary holds the computed statistics for one arm.
type armSummary struct {
	name         string
	runs         int
	avgCost      float64
	stdevCost    float64
	medianCost   float64
	avgTokens    float64
	criteriaRate float64 // 0–100
}

// analyzeRuns computes per-arm statistics from a slice of Run values and
// writes the formatted table to out. Extracted for unit-testability.
func analyzeRuns(taskID string, runs []db.Run, out io.Writer) error {
	// Group by arm
	byArm := make(map[string][]db.Run)
	armOrder := []string{}
	for _, r := range runs {
		if _, seen := byArm[r.Arm]; !seen {
			armOrder = append(armOrder, r.Arm)
		}
		byArm[r.Arm] = append(byArm[r.Arm], r)
	}

	summaries := make([]armSummary, 0, len(armOrder))
	for _, name := range armOrder {
		armRuns := byArm[name]
		n := float64(len(armRuns))

		var totalCost, totalTokens float64
		var totalPass, totalCriteriaTotal int
		costs := make([]float64, len(armRuns))
		for i, r := range armRuns {
			totalCost += r.TotalCostUSD
			totalTokens += float64(r.InputTokens + r.OutputTokens)
			totalPass += r.CriteriaPass
			totalCriteriaTotal += r.CriteriaTotal
			costs[i] = r.TotalCostUSD
		}

		avgCost := totalCost / n

		// Population stdev
		var variance float64
		for _, c := range costs {
			d := c - avgCost
			variance += d * d
		}
		stdev := math.Sqrt(variance / n)

		// Median
		sorted := make([]float64, len(costs))
		copy(sorted, costs)
		sort.Float64s(sorted)
		var median float64
		mid := len(sorted) / 2
		if len(sorted)%2 == 0 {
			median = (sorted[mid-1] + sorted[mid]) / 2
		} else {
			median = sorted[mid]
		}

		var criteriaRate float64
		if totalCriteriaTotal > 0 {
			criteriaRate = float64(totalPass) / float64(totalCriteriaTotal) * 100
		}

		summaries = append(summaries, armSummary{
			name:         name,
			runs:         len(armRuns),
			avgCost:      avgCost,
			stdevCost:    stdev,
			medianCost:   median,
			avgTokens:    totalTokens / n,
			criteriaRate: criteriaRate,
		})
	}

	// Sort by avg cost ascending
	sort.Slice(summaries, func(i, j int) bool {
		return summaries[i].avgCost < summaries[j].avgCost
	})

	// Baseline: "vanilla" if present, otherwise the cheapest arm (index 0 after sort)
	baselineIdx := 0
	for i, s := range summaries {
		if s.name == "vanilla" {
			baselineIdx = i
			break
		}
	}
	baseline := summaries[baselineIdx]

	// Count total runs
	totalRuns := 0
	for _, s := range summaries {
		totalRuns += s.runs
	}

	fmt.Fprintf(out, "Task: %s  (%d runs across %d arms)\n\n", taskID, totalRuns, len(summaries))

	tw := tabwriter.NewWriter(out, 0, 0, 2, ' ', 0)
	fmt.Fprintln(tw, "Arm\tRuns\tAvg Cost\tStdev\tMedian\tAvg Tok\tCriteria\tvs vanilla")
	fmt.Fprintln(tw, "---------------\t----\t--------\t------\t-------\t-------\t--------\t----------")

	for _, s := range summaries {
		var deltaStr string
		if s.name == baseline.name {
			deltaStr = "(baseline)"
		} else {
			delta := (s.avgCost - baseline.avgCost) / baseline.avgCost * 100
			if delta >= 0 {
				deltaStr = fmt.Sprintf("+%.1f%%", delta)
			} else {
				deltaStr = fmt.Sprintf("%.1f%%", delta)
			}
		}

		fmt.Fprintf(tw, "%s\t%d\t$%.3f\t$%.3f\t$%.3f\t%s\t%.1f%%\t%s\n",
			s.name,
			s.runs,
			s.avgCost,
			s.stdevCost,
			s.medianCost,
			formatTokens(int(math.Round(s.avgTokens))),
			s.criteriaRate,
			deltaStr,
		)
	}

	return tw.Flush()
}

// formatTokens formats an integer with comma separators.
func formatTokens(n int) string {
	s := fmt.Sprintf("%d", n)
	if len(s) <= 3 {
		return s
	}
	// Insert commas from right
	result := make([]byte, 0, len(s)+len(s)/3)
	start := len(s) % 3
	if start == 0 {
		start = 3
	}
	result = append(result, s[:start]...)
	for i := start; i < len(s); i += 3 {
		result = append(result, ',')
		result = append(result, s[i:i+3]...)
	}
	return string(result)
}
