package cli

import (
	"context"
	"database/sql"
	"flag"
	"fmt"
	"os"
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

func Run(args []string) error {
	if len(args) < 2 {
		return usage()
	}

	switch args[1] {
	case "run":
		return runCmd(args[2:])
	case "compare":
		return compareCmd(args[2:])
	case "history":
		return historyCmd(args[2:])
	case "tasks":
		return tasksCmd(args[2:])
	case "--help", "-h", "help":
		return usage()
	default:
		return fmt.Errorf("unknown subcommand %q; run with --help for usage", args[1])
	}
}

func usage() error {
	fmt.Println("token-miser: A/B test Claude Code configurations")
	fmt.Println()
	fmt.Println("Subcommands:")
	fmt.Println("  run      Run an experiment")
	fmt.Println("  compare  Compare results for a task")
	fmt.Println("  history  Show run history")
	fmt.Println("  tasks    List available tasks")
	return nil
}

func resolveDB(dbPath string) (string, error) {
	if dbPath != "" {
		return dbPath, nil
	}
	return db.DefaultDBPath()
}

func runCmd(args []string) error {
	fs := flag.NewFlagSet("run", flag.ContinueOnError)
	taskPath := fs.String("task", "", "path to task YAML file")
	control := fs.String("control", "vanilla", "control arm spec")
	treatment := fs.String("treatment", "", "treatment arm spec")
	model := fs.String("model", "sonnet", "model to use")
	dbPath := fs.String("db", "", "path to results DB (default: ~/.token_miser/results.db)")

	if err := fs.Parse(args); err != nil {
		return err
	}

	if *taskPath == "" {
		return fmt.Errorf("--task is required")
	}
	if *treatment == "" {
		return fmt.Errorf("--treatment is required")
	}

	t, err := task.LoadTask(*taskPath)
	if err != nil {
		return fmt.Errorf("load task: %w", err)
	}

	controlArm, err := arm.ParseArm(*control)
	if err != nil {
		return fmt.Errorf("parse control arm: %w", err)
	}

	treatmentArm, err := arm.ParseArm(*treatment)
	if err != nil {
		return fmt.Errorf("parse treatment arm: %w", err)
	}

	resolvedDB, err := resolveDB(*dbPath)
	if err != nil {
		return fmt.Errorf("resolve db path: %w", err)
	}

	database, err := db.InitDB(resolvedDB)
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	defer database.Close()

	apiKey := os.Getenv("ANTHROPIC_API_KEY")
	eval := evaluator.NewEvaluator(apiKey)

	arms := []*arm.Arm{controlArm, treatmentArm}
	for _, a := range arms {
		if err := runArm(t, a, *model, database, eval); err != nil {
			fmt.Fprintf(os.Stderr, "error running arm %q: %v\n", a.Name, err)
		}
	}

	return nil
}

func runArm(t *task.Task, a *arm.Arm, model string, database *sql.DB, eval *evaluator.Evaluator) error {
	fmt.Printf("\n=== Running arm: %s ===\n", a.Name)

	env, err := environment.SetupEnv(t, a)
	if err != nil {
		return fmt.Errorf("setup env: %w", err)
	}
	defer environment.TeardownEnv(env)

	startedAt := time.Now().UTC().Format(time.RFC3339)

	ctx := context.Background()
	result, err := executor.RunClaude(ctx, t.Prompt, env, model)
	if err != nil {
		return fmt.Errorf("run claude: %w", err)
	}

	criteriaResults := checker.EvaluateCriteria(t.SuccessCriteria, env)
	pass, total := 0, len(criteriaResults)
	for _, cr := range criteriaResults {
		if cr.Passed {
			pass++
		}
	}

	qualityScores, _ := evaluator.ScoreQuality(ctx, eval, t.QualityRubric, t.Prompt, env.WorkspaceDir)
	scoresJSON, _ := db.MarshalQualityScores(qualityScores)

	run := &db.Run{
		TaskID:           t.ID,
		Arm:              a.Name,
		LoadoutName:      a.LoadoutPath,
		Model:            model,
		StartedAt:        startedAt,
		WallSeconds:      result.WallSeconds,
		InputTokens:      result.InputTokens,
		OutputTokens:     result.OutputTokens,
		CacheReadTokens:  result.CacheReadTokens,
		CacheWriteTokens: result.CacheWriteTokens,
		TotalCostUSD:     result.TotalCostUSD,
		ExitCode:         result.ExitCode,
		CriteriaPass:     pass,
		CriteriaTotal:    total,
		QualityScores:    scoresJSON,
	}

	if _, err := db.StoreRun(database, run); err != nil {
		return fmt.Errorf("store run: %w", err)
	}

	fmt.Printf("  tokens: %d in / %d out | cost: $%.6f | wall: %.2fs\n",
		result.InputTokens, result.OutputTokens, result.TotalCostUSD, result.WallSeconds)
	fmt.Printf("  criteria: %d/%d passed\n", pass, total)
	return nil
}

func compareCmd(args []string) error {
	fs := flag.NewFlagSet("compare", flag.ContinueOnError)
	taskID := fs.String("task", "", "task ID to compare")
	dbPath := fs.String("db", "", "path to results DB")

	if err := fs.Parse(args); err != nil {
		return err
	}

	if *taskID == "" {
		return fmt.Errorf("--task is required")
	}

	resolvedDB, err := resolveDB(*dbPath)
	if err != nil {
		return fmt.Errorf("resolve db path: %w", err)
	}

	database, err := db.InitDB(resolvedDB)
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	defer database.Close()

	output, err := report.Compare(*taskID, database)
	if err != nil {
		return fmt.Errorf("compare: %w", err)
	}

	fmt.Print(output)
	return nil
}

func historyCmd(args []string) error {
	fs := flag.NewFlagSet("history", flag.ContinueOnError)
	taskID := fs.String("task", "", "filter by task ID")
	dbPath := fs.String("db", "", "path to results DB")

	if err := fs.Parse(args); err != nil {
		return err
	}

	resolvedDB, err := resolveDB(*dbPath)
	if err != nil {
		return fmt.Errorf("resolve db path: %w", err)
	}

	database, err := db.InitDB(resolvedDB)
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	defer database.Close()

	runs, err := db.GetRuns(database, *taskID)
	if err != nil {
		return fmt.Errorf("get runs: %w", err)
	}

	if len(runs) == 0 {
		fmt.Println("No runs found.")
		return nil
	}

	fmt.Printf("%-5s %-12s %-20s %-10s %-8s %-8s\n", "ID", "Task", "Started", "Arm", "In", "Out")
	for _, r := range runs {
		fmt.Printf("%-5d %-12s %-20s %-10s %-8d %-8d\n",
			r.ID, r.TaskID, r.StartedAt[:19], r.Arm, r.InputTokens, r.OutputTokens)
	}
	return nil
}

func tasksCmd(args []string) error {
	fs := flag.NewFlagSet("tasks", flag.ContinueOnError)
	dir := fs.String("dir", "tasks", "directory to scan for task YAML files")

	if err := fs.Parse(args); err != nil {
		return err
	}

	entries, err := os.ReadDir(*dir)
	if err != nil {
		return fmt.Errorf("read tasks dir: %w", err)
	}

	found := false
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		if len(name) < 5 || name[len(name)-5:] != ".yaml" {
			continue
		}
		path := *dir + "/" + name
		t, err := task.LoadTask(path)
		if err != nil {
			fmt.Printf("  %s (error: %v)\n", name, err)
			continue
		}
		fmt.Printf("  %-20s %s\n", t.ID, t.Name)
		found = true
	}

	if !found {
		fmt.Println("No tasks found.")
	}
	return nil
}
