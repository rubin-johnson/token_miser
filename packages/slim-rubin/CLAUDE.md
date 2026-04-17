# Claude Code Configuration

## How to Work

- Lead with the answer, explain after
- Challenge assumptions early — failing fast beats wasted effort
- If solving the wrong problem, call it out
- Never stop to ask "shall I proceed?" — just proceed
- Only pause for decisions that are hard to reverse AND high-stakes

## Quality

- Actually solve the problem — not the happy path, not "probably solved"
- Never weaken or delete a failing test; never change expectations without explaining why the old one was wrong
- Before "done": re-read the requirement, test failure inputs, find the simpler way
- No hardcoded returns, no over-mocking, no "it works in my head" without execution

## Token Efficiency

- Use grep/glob before reading full files — never read a file when a search answers it
- One tool call per step when possible; don't speculatively read files you might not need
- If 3+ tool calls without progress, stop and reassess
- No unsolicited summaries, no trailing questions, no preamble

## Code

- All code reads like a human wrote it — no AI patterns, excessive comments, or over-engineering
- TDD: tests first, always
- Solve what was asked, not the generalized version; no side quests
- Prefer editing existing files over creating new ones
- Update README when changing CLI interface — same commit, not follow-up
- Commit messages: concise, imperative mood; no AI co-author attribution

## Python

- pyenv for versions, uv for packages — no pip, poetry, pipenv
- Run ruff before committing

## Git

- In interactive sessions: show proposed changes and wait for confirmation before committing
- In autonomous sessions (--dangerously-skip-permissions): commit freely when tests pass
