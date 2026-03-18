package cli

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
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
		{"control", *controlSpec},
		{"treatment", *treatmentSpec},
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

		res, err := executor.RunClaude(t.Prompt, env.HomeDir)
		if err != nil {
			return fmt.Errorf("run claude: %w", err)
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
			Arm:           spec.name,
			InputTokens:   res.Usage.InputTokens,
			OutputTokens:  res.Usage.OutputTokens,
			TotalCostUSD:  res.TotalCostUSD,
			CriteriaPass:  passed,
			CriteriaTotal: total,
			QualityScores: qualityJSON,
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

	home, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("get home dir: %w", err)
	}
	dbPath := filepath.Join(home, ".token_miser", "results.db")

	database, err := db.InitDB(dbPath)
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
	fmt.Fprintln(out, "not implemented")
	return fmt.Errorf("not implemented")
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