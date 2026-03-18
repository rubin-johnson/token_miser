package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rubin-johnson/token_miser/internal/db"
)

func TestHistoryCommand_HeaderPresent(t *testing.T) {
	dir := t.TempDir()
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	dbDir := filepath.Join(dir, ".token_miser")
	os.MkdirAll(dbDir, 0755)
	d, _ := db.InitDB(filepath.Join(dbDir, "results.db"))
	d.StoreRun(&db.Run{
		TaskID:        "t1",
		Arm:           "control",
		InputTokens:   1,
		OutputTokens:  1,
		TotalCostUSD:  0.001,
		QualityScores: "{}",
	})

	var buf bytes.Buffer
	err := historyCommand([]string{}, &buf)
	if err != nil {
		t.Fatalf("historyCommand: %v", err)
	}
	out := buf.String()
	for _, h := range []string{"ID", "TaskID", "Arm", "Tokens", "Cost", "Timestamp"} {
		if !strings.Contains(out, h) {
			t.Errorf("missing column %q in output: %q", h, out)
		}
	}
}
