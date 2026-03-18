package cli

import (
	"fmt"
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
	fmt.Println("not implemented")
	return fmt.Errorf("not implemented")
}
