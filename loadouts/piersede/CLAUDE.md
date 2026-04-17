# Token-Efficient Operating Spec

Based on piersede/token-efficiency. Goal: complete tasks with minimum context, minimum tool use, minimum repeated reasoning, maximum verification.

## Primary Rules

1. Keep active context small
2. Never read full files unless unavoidable
3. Do not restate known information
4. No decorative prose — diffs, commands, and results over explanation
5. Prefer targeted retrieval over exploratory browsing
6. Prefer summaries, symbols, and line ranges over full dumps
7. Keep persistent instructions short and scoped
8. Clear/compact aggressively between unrelated tasks
9. Use subagents for noisy work
10. Verify with deterministic tools, not explanation

## Retrieval Strategy

Use this hierarchy — stop at the first level that answers the question:

1. **Project map / pre-index** — use if available for orientation
2. **LSP** — go-to-definition, find-references, symbol discovery; prefer over grep for code nav
3. **grep / targeted search** — exact identifiers, narrow before expanding
4. **Read exact lines** — specific line ranges only
5. **Read whole file** — only if truly unavoidable

Search before read. Narrow before expanding. Never read a whole file just to locate one function.

## File Reading Policy

- Never read a whole file to find one function, class, or error
- First isolate with search, symbols, references, or indices
- Large files: extract only the relevant region
- Large docs: read only the exact section needed
- Do not reload context already in the conversation

## Tool Use Minimization

- Every tool call has token cost — use fewer, higher-value calls
- Batch independent calls in parallel
- Prefer tools that accept filters, return summaries, support line ranges
- Avoid tools that dump full datasets or long schemas
- If many intermediate calls would enter context, write a script that returns only the distilled result
- Keep tool inventory lean: disable unused MCP servers, consolidate overlapping tools

## Subagent Delegation

Main agent handles: task control, planning, final integration, verification, user-facing output.

Delegate to subagents for noisy isolated work:
- Codebase exploration
- Log analysis
- Test investigation
- Documentation lookup
- Parallel hypothesis checking

Subagents return only concise findings. They are context firewalls.

Reserve agent teams for genuinely parallel interdependent work — never for serial tasks.

## Context Hygiene

### Session discipline
- Start: check headroom, identify only relevant files, plan if non-trivial, no exploratory wandering
- During: incremental edits, verify after meaningful changes, don't let noisy output accumulate
- End: record durable state only if needed, clear before unrelated work

### Compaction policy
Compact proactively — after completing a feature, resolving a bug, finishing research, or before switching topics.

Preserve: current objective, confirmed facts, chosen approach, outstanding issues, next steps.
Drop: exploratory dead ends, verbose logs, failed hypotheses (unless still relevant), conversational filler.

### Long-task pattern
For tasks that outgrow a clean session:
1. Write a compact state file (objective, completed work, decisions, remaining steps, verification status)
2. Clear context
3. Resume from state file + minimum fresh code context

## Noisy Data Filtering

- **Logs**: never dump raw. Filter for ERROR, WARN, stack traces, relevant timestamps first
- **Command output**: do not emit full stdout if only a fraction matters — pipe through head/tail, use --quiet flags
- **Large payloads** (JSON, traces, listings): write to file, analyse externally, return only compact summary + key fields

## CLAUDE.md Size Discipline

Root CLAUDE.md must stay under 200 lines / ~1000 tokens. Include only:
- Project purpose and high-level architecture
- Essential build/test/lint commands
- Critical constraints and non-obvious conventions

Move detailed guidance into path-scoped rule files. Keep heavy material (API refs, deployment notes, design history, generated docs) outside always-loaded context — load on demand only.

Do not include: style rules enforced by tooling, exhaustive file descriptions, large examples, long design history, generic clean-code advice.

## Output Policy

- Be direct — no filler, praise, apology, reassurance, or commentary
- Do not repeat the task back to the user
- No long explanations when a diff, command, or result suffices
- Prefer: concise plan, concrete edit, exact command, verification result, short state summary

## Verification Policy

Always prefer deterministic verification: tests, linters, type checks, build, targeted runtime checks.
Do not claim success without verification. If verification is impossible, state what remains unverified.

## Caching Awareness

- Keep stable material (instructions, project map, tool definitions) at the beginning
- Keep volatile material (current task, temporary findings) at the end
- Do not casually reorder or mutate stable prefix sections

## Default Workflow

1. Identify exact task
2. Check context headroom
3. Plan if non-trivial
4. Locate code via index/LSP/search
5. Read only necessary regions
6. Make the smallest valid change set
7. Verify with deterministic tools
8. Summarise only durable state
9. Clear before unrelated work

## Anti-Patterns

- Reading entire large files without narrowing scope first
- Keeping unrelated tasks in one session
- Pasting full docs into persistent context
- Duplicating instructions across root and scoped rules
- Letting the model wander the repo to "understand the project"
- Keeping unused tools enabled
- Running agent teams when one agent suffices
- Trusting unverified work
