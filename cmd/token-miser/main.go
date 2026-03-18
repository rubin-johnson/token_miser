package main

import (
	"os"

	"github.com/rubin-johnson/token_miser/internal/cli"
)

func main() {
	exitCode := cli.Run(os.Args[1:])
	os.Exit(exitCode)
}
