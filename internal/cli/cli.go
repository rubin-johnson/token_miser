package cli

import (
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/rubin-johnson/token_miser/internal/db"
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

func runCommand(args []string, out io.Writer) error {
	fmt.Fprintln(out, "not implemented")
	return fmt.Errorf("not implemented")
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

func dbPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("get home dir: %w", err)
	}
	return filepath.Join(home, ".token_miser", "results.db"), nil
}

func historyCommand(args []string, out io.Writer) error {
	path, err := dbPath()
	if err != nil {
		return err
	}
	database, err := db.InitDB(path)
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	defer database.Close()

	runs, err := database.GetRuns("")
	if err != nil {
		return fmt.Errorf("get runs: %w", err)
	}

	tw := tabwriter.NewWriter(out, 0, 0, 2, ' ', 0)
	fmt.Fprintln(tw, "ID\tTaskID\tArm\tTokens\tCost\tTimestamp")
	for _, r := range runs {
		fmt.Fprintf(tw, "%d\t%s\t%s\t%d\t$%.6f\t%s\n",
			r.ID,
			r.TaskID,
			r.Arm,
			r.InputTokens+r.OutputTokens,
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