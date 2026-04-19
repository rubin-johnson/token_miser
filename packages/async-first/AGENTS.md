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
