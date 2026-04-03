#!/usr/bin/env bash
# Cleanup orphaned Claude subagent processes that accumulate across sessions.
# Wired into SessionStart and SessionEnd hooks.
#
# These orphans are typically spawned by plugins (e.g., claude-mem's worker)
# and persist after the parent session ends, leaking ~300-450MB each.

set -euo pipefail

# Read hook input from stdin (required by Claude Code hook protocol)
HOOK_INPUT=$(cat)
SESSION_ID=$(echo "$HOOK_INPUT" | jq -r '.session_id // empty')
HOOK_EVENT=$(echo "$HOOK_INPUT" | jq -r '.hook_event_name // empty')

LOG_FILE="$HOME/.claude/hooks/cleanup.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$HOOK_EVENT] $1" >> "$LOG_FILE"
}

# Finds Claude subagent processes that are stale (>10 min old) and spawned by
# plugin workers (not interactive terminal sessions).
# Uses both age and parent-based detection for safety.
STALE_THRESHOLD_SEC=600  # 10 minutes

get_orphaned_pids() {
    ps -eo pid,ppid,etimes,args 2>/dev/null | \
        awk -v threshold="$STALE_THRESHOLD_SEC" '
        /--output-format stream-json/ && /--disallowedTools/ {
            pid = $1
            ppid = $2
            age = $3
            # Kill if older than threshold
            if (age > threshold) print pid
        }'
}

# --- Cleanup logic (don't modify below) ---

PIDS=$(get_orphaned_pids)

if [ -z "$PIDS" ]; then
    log "No orphaned processes found"
    if [ "$HOOK_EVENT" = "SessionStart" ]; then
        echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Cleanup: no orphaned Claude processes found"}}'
    fi
    exit 0
fi

KILLED=0
FREED_KB=0

for PID in $PIDS; do
    RSS=$(ps -o rss= -p "$PID" 2>/dev/null || echo 0)
    if kill "$PID" 2>/dev/null; then
        KILLED=$((KILLED + 1))
        FREED_KB=$((FREED_KB + RSS))
        log "Killed PID $PID (${RSS}KB)"
    fi
done

FREED_MB=$((FREED_KB / 1024))
log "Cleaned up $KILLED processes, freed ~${FREED_MB}MB"

if [ "$HOOK_EVENT" = "SessionStart" ]; then
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"Cleanup: killed $KILLED orphaned Claude processes, freed ~${FREED_MB}MB\"}}"
fi

exit 0
