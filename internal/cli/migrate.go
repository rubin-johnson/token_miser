package cli

import (
	"flag"
	"fmt"
	"io"

	"github.com/rubin-johnson/token_miser/internal/db"
)

func migrateCommand(args []string, out io.Writer) error {
	fs := flag.NewFlagSet("migrate", flag.ContinueOnError)
	dbFlag := fs.String("db", "", "path to database file (default: ~/.token_miser/results.db)")
	if err := fs.Parse(args); err != nil {
		return err
	}
	path := *dbFlag
	if path == "" {
		path = dbPath()
	}
	if _, err := db.InitDB(path); err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	fmt.Fprintln(out, "migrations applied")
	return nil
}
