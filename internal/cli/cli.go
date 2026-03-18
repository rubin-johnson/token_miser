package cli

import (
	"flag"
	"fmt"
	"os"
)

// Run executes the CLI with the given arguments
func Run(args []string) int {
	if len(args) == 0 {
		printUsage()
		return 0
	}

	// Parse global flags
	fs := flag.NewFlagSet("token-miser", flag.ContinueOnError)
	fs.Usage = printUsage
	help := fs.Bool("help", false, "show help")

	if err := fs.Parse(args); err != nil {
		return 1
	}

	if *help || len(fs.Args()) == 0 {
		printUsage()
		return 0
	}

	subcmd := fs.Args()[0]
	subargs := fs.Args()[1:]

	switch subcmd {
	case "run":
		return runCommand(subargs)
	case "compare":
		return compareCommand(subargs)
	case "history":
		return historyCommand(subargs)
	case "tasks":
		return tasksCommand(subargs)
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", subcmd)
		printUsage()
		return 1
	}
}

func printUsage() {
	fmt.Println("Usage: token-miser [--help] <command> [args...]")
	fmt.Println("")
	fmt.Println("Commands:")
	fmt.Println("  run      Execute token analysis")
	fmt.Println("  compare  Compare token usage")
	fmt.Println("  history  Show usage history")
	fmt.Println("  tasks    Manage tasks")
	fmt.Println("")
	fmt.Println("Use --help for more information.")
}

func runCommand(args []string) int {
	fmt.Println("not implemented")
	return 1
}

func compareCommand(args []string) int {
	fmt.Println("not implemented")
	return 1
}

func historyCommand(args []string) int {
	fmt.Println("not implemented")
	return 1
}

func tasksCommand(args []string) int {
	fmt.Println("not implemented")
	return 1
}
