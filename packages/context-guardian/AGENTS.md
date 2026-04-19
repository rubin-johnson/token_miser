# Context Guardian

Minimize context window growth. Reuse what you've already read. Prune what's stale.

## File Reuse

- Once a file is read in this session, never read it again unless you have reason to believe it changed.
- Reference prior reads by filename + line range. Do not re-fetch to "double-check."
- If you edited a file, treat the edited version as known — do not re-read to confirm the edit.

## Session Indexing

- On first tool call in a new repo, run: `find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.go" -o -name "*.md" \) | head -60` to build a mental map.
- Reference that index for navigation; only re-explore if the structure changes.
- Do not grep for files you could locate from the index.

## Context Pruning

- Every 5 tool calls, ask: is everything in my active context still relevant to the current objective?
- Drop: exploratory dead ends, verbose logs, failed hypotheses, unrelated files.
- Keep: current objective, confirmed decisions, next 2 steps.
- Write a compact state note to `/tmp/session-state.md` before switching topics or after major milestones: objective, completed work, current approach, next steps.

## Session Boundaries

- Start a new session when switching to an unrelated task. Don't carry stale context forward.
- Before any compaction: write state note. After compaction: resume from state note + minimum fresh code context.
- If context feels bloated, it is — compact before continuing.
