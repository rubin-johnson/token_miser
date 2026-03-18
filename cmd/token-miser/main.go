package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/rubin-johnson/token_miser/internal/cli"
)

func main() {
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: %s [options] <command>\n\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "Commands:\n")
		fmt.Fprintf(os.Stderr, "  run      Execute token analysis (not implemented)\n")
		fmt.Fprintf(os.Stderr, "  compare  Compare token usage (not implemented)\n")
		fmt.Fprintf(os.Stderr, "  history  Show usage history (not implemented)\n")
		fmt.Fprintf(os.Stderr, "  tasks    List available tasks (not implemented)\n")
		fmt.Fprintf(os.Stderr, "\nOptions:\n")
		flag.PrintDefaults()
	}

	help := flag.Bool("help", false, "Show help message")
	flag.Parse()

	if *help || len(flag.Args()) == 0 {
		flag.Usage()
		os.Exit(0)
	}

	command := flag.Args()[0]
	args := flag.Args()[1:]

	if err := cli.Dispatch(command, args, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
