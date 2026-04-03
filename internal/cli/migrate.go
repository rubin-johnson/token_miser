package cli

import (
	"fmt"
	"io"

	"github.com/rubin-johnson/token_miser/internal/db"
)

func migrateCommand(args []string, out io.Writer) error {
	_ = args
	_, err := db.InitDB(dbPath())
	if err != nil {
		return fmt.Errorf("init db: %w", err)
	}
	return nil
}
