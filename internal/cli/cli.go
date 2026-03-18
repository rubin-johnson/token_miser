package cli

import (
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

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