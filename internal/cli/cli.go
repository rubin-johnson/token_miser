package cli

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/rubin-johnson/token_miser/internal/task"
)

// Dispatch routes commands to their handlers
func Dispatch(command string, args []string) error {
	switch command {
	case "run":
		return runCommand(args)
	case "compare":
		return compareCommand(args)
	case "history":
		return historyCommand(args)
	case "tasks":
		return tasksCommand(args)
	default:
		return fmt.Errorf("unknown command: %s", command)
	}
}

func runCommand(args []string) error {
	fmt.Println("not implemented")
	return fmt.Errorf("not implemented")
}

func compareCommand(args []string) error {
	fmt.Println("not implemented")
	return fmt.Errorf("not implemented")
}

func historyCommand(args []string) error {
	fmt.Println("not implemented")
	return fmt.Errorf("not implemented")
}

func tasksCommand(args []string) error {
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
		fmt.Printf("%-20s %s\n", t.ID, t.Name)
	}
	return nil
}
