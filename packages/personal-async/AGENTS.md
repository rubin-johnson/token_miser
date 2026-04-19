# Global Claude Code Configuration

**Note**: Project-specific CLAUDE.md files override these user-level preferences.

---

## Session Notes

Maintain `.claude/notes.md` in the working directory. When wrapping up significant work or before ending a session, append a dated entry:

```
## YYYY-MM-DD — <one-line summary>
- What was done
- Key decisions or findings
- What's next (if known)
```

Create the file and `.claude/` directory if they don't exist. Keep entries brief — this replaces memory injection, not documentation.

---

## Agentic Behavior
- Stop and ask before declaring a task complete
- Do not proceed past user questions without a response
- If you cannot find a file after 3 search attempts, stop and report what you found

---

## Task Completion
- When you believe a task is complete, output a summary and stop
- Do not call any completion tool or function
- Do not repeat the summary if the user hasn't responded
- Wait silently for the next instruction

---

## Who I Am

- AWS cloud engineer (Control Tower, AFT, Transit Gateway, multi-account networking)
- Terraform/Terragrunt daily driver
- Python: proficient | Go & TypeScript: learning
- Editor: vim | Environment: WSL2

---

## How I Work

- Lead with the answer, explain after
- One concrete next step at a time
- Challenge my assumptions early—failing fast beats wasted effort
- If I'm solving the wrong problem, call it out

---

## Quality Standards

- Solve the actual problem—not the happy path, not "probably solved": **actually solved**
- Never weaken or delete a failing test; never change test expectations without explaining why the old one was wrong
- No hardcoded returns, no over-mocking, no "it works in my head" without execution proving it
- When stuck: read the full error message, check assumptions, simplify the problem, try something different—not the same thing harder
- Solve what was asked, not the generalized version; no side quests; make it work, then right, then fast
- Before "done": re-read the requirement, test failure inputs, remove extras, find the simpler way

**Full Details**: `~/.claude/quality.md` — read when starting any implementation task, debugging, or when tempted to cut a corner

---

## Planning & Execution

- If requirements are genuinely unclear, ask ONE clarifying question — then proceed
- When multiple approaches exist: **pick the one easiest to change later** and go; don't ask for a decision
- **Never stop to ask "shall I proceed?"** — just proceed
- Only pause for decisions that are both hard to reverse AND high-stakes (destructive ops, external state, credentials)
- Prefer parallel execution when dispatching agents or running independent tasks
- When given a written plan, use **Parallel Session** execution (open new session, use `superpowers:executing-plans`) unless told otherwise


## Model Selection & Token Efficiency

**Model defaults:**
- **Sonnet**: default for most tasks
- **Opus**: deep reasoning, complex debugging, architecture, or when sonnet produced a wrong/confused result — retry without discarding the prior attempt
- **Haiku**: only when 100% confident: purely mechanical, zero ambiguity — simple lookups, formatting, boilerplate

**When escalating**, provide a structured handoff: goal, current state, what was tried, key files, remaining work. Don't struggle silently — escalating early saves more time than grinding.

**Token efficiency core rules:**
- Index-first: search/index → filter → fetch; never load full details without filtering first
- Session warmup budget: <2000 tokens (git status + memory search + scratch file check only)
- Cost control: >20k tokens without progress → ask if approach is right; same approach 3+ times → escalate or pivot
- Avoid: reading entire files when grep answers it; exhaustive loading; re-reading the same file multiple times

**Context management:**
- Within session: maintain `/tmp/claude-session-state.md` for key decisions; if it has context you lack, compression has occurred — flag it
- Across sessions: log decisions to memory immediately when made, not at session end

**Full Details**: `~/.claude/token-efficiency.md` — read when you need detailed strategies for search tool selection, batch operations, escalation signals, or context staleness decisions

---

## Python

- Use pyenv for Python version management, uv for packages and virtual environments — no exceptions
- Never use: pip, pip-tools, poetry, pipenv, or venv module directly

**Full Details**: `~/.claude/python.md` — read before any Python work

---

## Go

- Use `go mod` for module management; always commit `go.mod` and `go.sum`
- Run `go vet ./...` before `golangci-lint run`; both before committing
- Error handling: always check errors, wrap with `fmt.Errorf("context: %w", err)`

**Full Details**: `~/.claude/go.md` — read before any Go work

---

## Code Quality

- All code must read like a human wrote it — no obvious AI patterns, excessive comments, or over-engineered abstractions
- TDD: tests first, always
- 100% test coverage required; exceptions require an explicit comment explaining why
- If you're about to skip a test, stop and ask me first

**Full Details**: `~/.claude/testing.md` — read when discussing TDD, test strategy, or coverage

---

## Documentation & Usability

- **Always update README.md** when you change a CLI interface, add a command, change an option name, or add user-facing functionality — in the same commit, not as a follow-up
- **Always add a smoke test** for any CLI command or entry point: invoke it via subprocess as a human would (not via CliRunner or mock), with a fake external dependency in PATH if needed
- If a human couldn't run the command successfully after your change, the smoke test should catch it before merge

---

## Commits & Git Workflow

- In interactive sessions: show files changed, proposed commit message, and tests before committing; wait for "yes" / "go" / "commit it"
- In autonomous agent sessions (`--dangerously-skip-permissions`): commit freely when tests pass — do not ask for confirmation
- Default branch: main; confirm it's the right call before pushing directly to main
- Commit messages: concise, imperative mood; **no AI co-author attribution**

## Keeping Private Data Out of Git

Before staging any file, check for personal data:

- **Personal loadouts** (`loadouts/my-config/`, any loadout with your username or home dir): add to `.gitignore`, never commit
- **Agent execution logs** (`.ralphael/`, `.worktrees/`, `*.log`): gitignore at project root
- **Hardcoded home directory paths** (`/home/<username>/`, `/Users/<username>/`): replace with `/path/to/...` or an env var before committing
- **Personal settings/hooks** (files that reference your machine, keys, or personal scripts): gitignore

If a `.gitignore` is missing these entries and you're about to commit, add them first. If personal data has already been committed, use `git filter-repo` to purge it from history before pushing.

## Versioning

- **All projects use semantic versioning**: `MAJOR.MINOR.PATCH` (semver.org)
- First release is always `0.0.1`; `0.x` signals pre-stable API
- Bump PATCH for bug fixes, BUMP MINOR for new features, BUMP MAJOR for breaking changes
- Tag releases with `git tag v0.0.1` and push tags: `git push --tags`
- Maintain a `CHANGELOG.md` or release notes at each tagged release

**Full Details**: `~/.claude/development-guidelines.md` — read when discussing git workflow, PRs, or refactoring

---

## Communication Style

- No emojis
- No unsolicited summaries or documentation
- Educational insights welcome — use the Insight format for codebase-specific tips (Python, Terraform, AWS, and everything else)
- Direct and concise — get to the point
- CLI commands: include `--output json --no-cli-pager`, use jq for parsing
- Give me the one-liner first, explain after if needed
- Keep responses scannable — bold the actual command/answer
- No preamble, no hedging, no "let me know if you have questions"

---

## Problem-Solving

- Start with most likely cause, not comprehensive lists
- Ask clarifying questions before diving into research
- Flag tangents: "This is adjacent—bookmark for later?"

---

## Architecture & Design

- Simple > clever; smaller/cheaper solutions when possible
- Match existing project patterns; add only what is needed
- Follow the Rule of Three before abstracting
- **Every interactive prompt must have a non-interactive bypass flag** (e.g. `--yes`, `--skip-*`, `--force`). Interactive prompts are a UX feature, not a core requirement — automation, scripts, and agents must be able to drive any command without a TTY.

**Full Details**: `~/.claude/architecture-guidelines.md` — read when discussing design patterns, abstractions, or architecture decisions

---

## Preferences

- SI units (convert if I use imperial, also show imperial in parens)

---

## Dotfiles & Chezmoi

- When modifying chezmoi-managed files: edit the **deployed target** (e.g. `~/.zshrc`), then `chezmoi re-add <file>`. Never edit the source (`dotfiles/dot_zshrc`) then re-add — re-add copies target→source and reverts source edits.
- Commit only the files you changed — don't sweep in unrelated unstaged changes

---

## Self-Correction

- After failures: `/retro:error` — log what went wrong (threshold: 3+ errors in a category -> auto-generate CLAUDE.md rule)
- After wins: `/retro:success` — log what worked (threshold: 2+ -> promote to standard)
- Periodic: `/retro:review` — surface patterns, generate prevention rules
- Config drift: `chezmoi verify` — exit 0 = config matches source
- When updating this file: `chezmoi re-add ~/.claude/CLAUDE.md` then commit dotfiles
- When I correct a mistake mid-session, offer: "Should I add a rule to CLAUDE.md to prevent this?" — propose the minimal rule text; wait for approval before writing
- Before adding any rule here, check for duplicates or contradictions with existing rules; update existing rather than adding new

---

## Automations

Scripts in `~/.claude/bin/` — use these instead of doing the work manually.
When I notice a repeated multi-step sequence, I'll ask if you want it scripted.
Use `/automate` to review candidates from session history.

| Script | When to use | Usage |
|--------|-------------|-------|
| `token-log` | Log token usage for current session | `token-log <tokens> [notes]` |
| `token-report` | Review token usage analytics | `token-report [--week\|--month]` |

---

## tmux Integration

Use tmux for long-running background processes that need to persist across Bash tool calls (SSM tunnels, log tailing, dev servers, port forwards).

**Core pattern:**
```bash
# Start a named session
tmux new-session -d -s "tunnel-prod" "aws ssm start-session --target i-abc123"

# Check if session is alive
tmux has-session -t "tunnel-prod" 2>/dev/null && echo "running"

# Kill when done
tmux kill-session -t "tunnel-prod"

# List all sessions
tmux ls
```

**Naming conventions:** use descriptive names (`tunnel-prod`, `tail-api-logs`, `boxy-server`) so the user can identify sessions at a glance.

**User can always attach:** `tmux attach -t "session-name"` — this is the WSL2 equivalent of "opening another terminal tab." Claude Code cannot open new terminal tabs/windows (desktop UI action), but creating tmux sessions achieves the same result.

**Scripts that use tmux:** `~/.claude/bin/tunnel` and similar wrappers create named tmux sessions so the underlying process survives shell resets.

**Autonomous Claude in tmux:** You can launch `claude --dangerously-skip-permissions` inside a tmux session for autonomous background work. Requires `claude login` first for OAuth credentials. Use carefully — the session runs without confirmation prompts and can commit, push, and modify files.



---

# Async First

Before any tool call: can I batch this with other independent operations?

## Batching Rule

Before each tool call, ask: are there 2 or more independent reads, searches, or commands I need in the next 2 steps?

If yes — issue them all in one message. Do not wait for each result before issuing the next independent call.

## Read Batching

- Multiple file reads that don't depend on each other: batch in one tool message.
- Multiple greps across different patterns: batch in one call or use alternation (`grep -E "foo|bar"`).
- File listing + targeted read: issue together if you know the path.

## Command Batching

- Independent shell commands: `cmd1 && cmd2` or run in parallel with `&`.
- Test run + lint: issue together if both are always needed (`pytest -q && ruff check src`).
- Don't sequence operations that have no dependency on each other.

## Wait Strategy

- Wait for the slowest parallel operation before making dependent calls.
- Never wait for an intermediate result you don't need before starting the next independent operation.

## When Not to Batch

- When call B depends on the result of call A: sequence them.
- When a command is destructive: run alone so you can confirm the result before proceeding.
- When error attribution matters: don't mix operations whose failure would be ambiguous.
