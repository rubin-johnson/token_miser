#!/bin/bash
#
# Session-end hook: Automatically log token usage and cost
# Runs at the end of every Claude Code session
#

set -euo pipefail

# Read hook input (Claude Code pipes session JSON to stdin)
HOOK_INPUT=$(cat 2>/dev/null || echo '{}')

# Database location
DB="$HOME/.claude/token-usage.db"

# Initialize database if it doesn't exist
if [ ! -f "$DB" ]; then
    sqlite3 "$DB" <<'EOF'
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    date TEXT NOT NULL,
    working_dir TEXT,
    git_repo TEXT,
    git_branch TEXT,
    category TEXT,
    tokens_total INTEGER,
    cost_usd REAL,
    account TEXT DEFAULT 'work',
    model TEXT,
    session_duration_seconds INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS credit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    date TEXT NOT NULL,
    amount_usd REAL NOT NULL,
    account TEXT DEFAULT 'work',
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_date ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_category ON sessions(category);
CREATE INDEX IF NOT EXISTS idx_repo ON sessions(git_repo);
CREATE INDEX IF NOT EXISTS idx_account ON sessions(account);
EOF
fi

# Migrate existing DB: add new columns if missing (fails silently if already present)
sqlite3 "$DB" "ALTER TABLE sessions ADD COLUMN cost_usd REAL;" 2>/dev/null || true
sqlite3 "$DB" "ALTER TABLE sessions ADD COLUMN account TEXT DEFAULT 'work';" 2>/dev/null || true
sqlite3 "$DB" "ALTER TABLE sessions ADD COLUMN model TEXT;" 2>/dev/null || true
sqlite3 "$DB" "CREATE TABLE IF NOT EXISTS credit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    date TEXT NOT NULL,
    amount_usd REAL NOT NULL,
    account TEXT DEFAULT 'work',
    notes TEXT
);" 2>/dev/null || true

# Capture session context
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S")
DATE=$(date -u +"%Y-%m-%d")
WORKING_DIR=$(pwd)
ACCOUNT="${CLAUDE_ACCOUNT:-work}"

# Extract cost, tokens, and model from hook JSON (fall back to env vars if not present)
COST_USD=$(echo "$HOOK_INPUT" | jq -r '.cost.total_cost_usd // "0"' 2>/dev/null || echo "0")
MODEL=$(echo "$HOOK_INPUT" | jq -r '.model // ""' 2>/dev/null || echo "")
TOTAL_IN=$(echo "$HOOK_INPUT" | jq -r '.context_window.total_input_tokens // 0' 2>/dev/null || echo "0")
TOTAL_OUT=$(echo "$HOOK_INPUT" | jq -r '.context_window.total_output_tokens // 0' 2>/dev/null || echo "0")
TOKENS_TOTAL=$(( TOTAL_IN + TOTAL_OUT ))

# Fall back to env var if hook JSON had no token data
if [[ "$TOKENS_TOTAL" -eq 0 ]]; then
    TOKENS_TOTAL="${CLAUDE_SESSION_TOKENS:-0}"
fi

SESSION_DURATION="${CLAUDE_SESSION_DURATION:-0}"

# Try to get git info
GIT_REPO=""
GIT_BRANCH=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    GIT_REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo '')")
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')
fi

# Auto-categorize based on directory/repo
CATEGORY="general"
case "$WORKING_DIR" in
    *terraform*) CATEGORY="terraform" ;;
    *arium_code*) CATEGORY="arium-infrastructure" ;;
    *cc_code*) CATEGORY="crowncastle-infrastructure" ;;
    *.claude*) CATEGORY="claude-config" ;;
    *python*) CATEGORY="python-development" ;;
    */go/*) CATEGORY="go-development" ;;
    */typescript*) CATEGORY="typescript-development" ;;
esac

# Log to database
sqlite3 "$DB" <<EOF
INSERT INTO sessions (
    timestamp, date, working_dir, git_repo, git_branch,
    category, tokens_total, cost_usd, account, model, session_duration_seconds, notes
) VALUES (
    '$TIMESTAMP', '$DATE', '$WORKING_DIR', '$GIT_REPO', '$GIT_BRANCH',
    '$CATEGORY', $TOKENS_TOTAL, $COST_USD, '$ACCOUNT', '$MODEL', $SESSION_DURATION, ''
);
EOF

# Print credit summary to stderr (visible in terminal after session ends)
# Only show if we have cost data for this session
if [[ "$COST_USD" != "0" ]] && [[ -n "$COST_USD" ]]; then
    CREDIT_INFO=$(sqlite3 "$DB" <<EOF 2>/dev/null
SELECT
    printf('%.2f', COALESCE(SUM(ce.amount_usd), 0)) as loaded,
    printf('%.2f', COALESCE((SELECT SUM(cost_usd) FROM sessions WHERE account = '$ACCOUNT' AND cost_usd IS NOT NULL), 0)) as spent,
    printf('%.2f', COALESCE(SUM(ce.amount_usd), 0) - COALESCE((SELECT SUM(cost_usd) FROM sessions WHERE account = '$ACCOUNT' AND cost_usd IS NOT NULL), 0)) as balance
FROM credit_events ce WHERE ce.account = '$ACCOUNT';
EOF
    )

    LOADED=$(echo "$CREDIT_INFO" | cut -d'|' -f1)
    SPENT=$(echo "$CREDIT_INFO" | cut -d'|' -f2)
    BALANCE=$(echo "$CREDIT_INFO" | cut -d'|' -f3)

    COST_FMT=$(printf '$%.2f' "$COST_USD")

    if [[ "$LOADED" == "0.00" ]]; then
        echo "session: ${COST_FMT} — run \`credits-add <amount>\` to track API balance" >&2
    else
        echo "session: ${COST_FMT} | ${ACCOUNT} credits: \$${BALANCE} remaining (\$${SPENT}/\$${LOADED} used)" >&2
    fi
fi

# Check for chezmoi drift and uncommitted dotfiles changes
DOTFILES="$HOME/dotfiles"
if command -v chezmoi &>/dev/null && ! chezmoi verify 2>/dev/null; then
    echo "dotfiles: chezmoi drift detected — run 'chezmoi re-add <file>'" >&2
fi
if [ -d "$DOTFILES/.git" ]; then
    DOTFILES_DIRTY=$(git -C "$DOTFILES" status --porcelain -- private_dot_claude/ 2>/dev/null | wc -l | tr -d ' ')
    if [ "$DOTFILES_DIRTY" -gt 0 ]; then
        echo "dotfiles: $DOTFILES_DIRTY uncommitted change(s) in private_dot_claude/ — commit before they're lost" >&2
    fi
fi

# Nudge retro review if enough unreviewed entries have accumulated
RETRO_DB="$HOME/.retro/retro.db"
if [ -f "$RETRO_DB" ]; then
    LAST_REVIEWED=$(sqlite3 "$RETRO_DB" "SELECT value FROM metadata WHERE key = 'last_reviewed_at'" 2>/dev/null || echo "")
    if [ -n "$LAST_REVIEWED" ]; then
        UNREVIEWED=$(sqlite3 "$RETRO_DB" "SELECT COUNT(*) FROM entries WHERE created_at > '$LAST_REVIEWED'" 2>/dev/null || echo "0")
    else
        UNREVIEWED=$(sqlite3 "$RETRO_DB" "SELECT COUNT(*) FROM entries" 2>/dev/null || echo "0")
    fi
    if [ "$UNREVIEWED" -ge 5 ] 2>/dev/null; then
        echo "retro: $UNREVIEWED unreviewed entries — run /retro:review" >&2
    fi
fi

exit 0
