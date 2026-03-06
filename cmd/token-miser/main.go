package main

import (
	"fmt"
	"os"

	"github.com/rubin-johnson/token_miser/internal/cli"
)

func main() {
	if err := cli.Run(os.Args); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}
