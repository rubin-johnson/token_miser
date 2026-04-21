# Claude Code Configuration

## Execution Constraints

- Tool-call budget: max 50 per task
- Plan in 3-5 bullets before implementing
- One logical change per tool call
- If stuck after 3 attempts, try a different approach
- No explanatory text between tool calls unless reporting a finding
- Skip confirmation — proceed unless destructive + irreversible

## Efficiency

- Prefer grep/glob over reading entire files
- Never re-read a file already in context
- Use line-range reads for large files
- Batch independent tool calls in a single message
- Run tests after each change

## Communication

- Lead with the answer, explain after
- No emojis, no preamble, no hedging
- Direct and concise — bold the actual command/answer
- Challenge assumptions; if solving the wrong problem, say so

## Code

- TDD: tests first, always
- Simple > clever; match existing patterns; Rule of Three before abstracting
- No AI patterns, excessive comments, or over-engineering
- Solve what was asked — no side quests

## Python

- pyenv for versions, uv for packages — no exceptions
- Type hints on function signatures
- Imports: stdlib, third-party, local (isort order)

## Git

- Commit messages: concise, imperative mood; no AI co-author attribution
- Interactive sessions: show changes and wait for confirmation
- Autonomous sessions: commit freely when tests pass
