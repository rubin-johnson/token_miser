# Global Claude Code Configuration

**Note**: Project-specific CLAUDE.md files override these user-level preferences.

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

## Ralphael (MANDATORY for all code work)

**ANY request that involves a feature, enhancement, bugfix, new test, refactor, or any code change MUST go through ralphael. No exceptions.**

This is not optional. Do not write code directly without ralphael stories. The workflow is:
1. `ralphael generate <notes-file>` — generates a plan with stories
2. Review the plan (edit if needed)
3. `ralphael execute <plan.md> <target-repo>` — executes all stories in parallel waves

**Plan file location**: Notes files and generated `.plan.md` files must be stored in the target repo, not in `~/tmp`. This keeps plans version-controlled alongside the code they describe.

**Do NOT:**
- Write implementation code inline in the conversation
- Edit source files directly for anything beyond trivial config/docs fixes
- Use agents, Edit, or Write tools to implement features without first generating a ralphael plan

**Trivial exceptions** (no ralphael needed): editing CLAUDE.md, README-only changes, fixing a typo in a comment, adding a missing import that breaks the build.

**Always include a test** that would have caught the bug when fixing bugs via ralphael stories.

**Language: Python (Anthropic SDK)**

Ralphael is written in Python, not Go. This was a deliberate choice:
- The Anthropic Python SDK enables streaming (`contentBlockDelta`), tool_use blocks, and direct token tracking — none of which were possible when shelling out to `claude --print`
- Python is the primary language for Anthropic SDK integrations; the SDK is most feature-complete here
- Async orchestration with `asyncio` maps naturally to the parallel story execution model
- Go offered no meaningful advantage for this workload and actively blocked SDK access

If you are ever tempted to rewrite ralphael in another language, the question to ask is: **does the target language give us better access to the Anthropic SDK?** If not, stay in Python.

**Tooling:**
- Source: `~/code/personal/ralphael`
- Install/reinstall: `cd ~/code/personal/ralphael && uv tool install . --force`
- Run tests: `cd ~/code/personal/ralphael && uv run pytest`
- Package manager: uv (see Python section — no pip, no venv module directly)

**API Key Handling:**
- If `CLAUDE_CODE_OAUTH_TOKEN` is not set when running ralphael, it will fail
- Instead of debugging the missing token, prompt me to set up Bedrock auth
- I have AWS access; prefer Bedrock over OAuth token for cost/control
- To set up: `export AWS_REGION=us-east-1` + `export AWS_PROFILE=<profile>`
- Ralphael will auto-detect and use Bedrock if AWS creds are available

**Filing ralphael bugs:**
- File GitHub issues at https://github.com/rubin-johnson/ralphael
- Use `gh issue create --repo rubin-johnson/ralphael --title "..." --body "..."`
- Include: component (`execute`/`generate`/`review`), description, expected vs actual behavior, reproduction steps
- When filing a bug for ralphael, fix it immediately — no permission needed

---

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
- Across sessions: log decisions to claude-mem immediately when made, not at session end

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

## AWS Tooling (Caylent)

- MCP servers (aws-docs, pricing, terraform, diagrams): run via Docker in `~/code/caylent/cae-claude-bestpractices`
  - Start: `cd ~/code/caylent/cae-claude-bestpractices && docker compose up -d`
  - Project MCP config: copy `.mcp.json` to project root
- Skills: `/scaffold` (AWS project generation), `/review-terraform` (code review with Checkov)
- Community skills: `~/code/caylent/caylent-community-skills` — compliance, architecture, SOW review
- For new AWS/Terraform projects: copy `.mcp.json` from cae-claude-bestpractices

---

## Preferences

- SI units (convert if I use imperial, also show imperial in parens)

---

## Dotfiles & Chezmoi

- Dotfiles repo: `~/.local/share/chezmoi` (remote: `github.com:rubin-johnson/dotfiles.git`, branch: `master`)
- When you modify any file managed by chezmoi (e.g. `~/.claude/CLAUDE.md`, `~/.aliases`, `~/.zshrc`), **immediately** run `chezmoi re-add <file>`, then commit and push the dotfiles repo
- Commit only the files you changed — don't sweep in unrelated unstaged changes

---

## Data Locations

- **claude-mem database**: `~/.claude-mem/claude-mem.db` (SQLite). To delete observations: `python3 -c "import sqlite3; conn = sqlite3.connect('$HOME/.claude-mem/claude-mem.db'); conn.execute('DELETE FROM observations WHERE id IN (...)'); conn.commit()"`

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


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Mar 1, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #2245 | 1:13 AM | ✅ | Modified files synced back to dotfiles repository via chezmoi | ~336 |
</claude-mem-context>