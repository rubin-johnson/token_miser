# Fail Smart

Treat failures as data. Extract maximum information before retrying. Enumerate failure modes before testing.

## Error-First Protocol

When a command fails:
1. Read the full error output — all of it. Don't re-run.
2. Extract: error type, file and line, expected vs actual, any stack trace frames.
3. Form one specific hypothesis. State it in one line.
4. Make one targeted fix. Re-run.
5. If still failing, re-read the full new error before forming the next hypothesis.

Never retry the same command without a specific reason why the next run will differ.

## Failure Mode Enumeration

Before implementing any feature or fix, write 3–5 ways it could fail:
- Input validation failures
- Edge cases (empty, zero, max, concurrent)
- Integration points (DB, API, file system)
- State assumptions that could be wrong

Write at least one test for each failure mode before running the suite. If a failure mode has no test, add it before declaring done.

## Incremental Verification

- After each logical code change, run targeted verification: `pytest -k <test_name>`, `mypy <file>`, `ruff check <file>`.
- Don't wait for end-of-task full suite runs — catch failures at the change that caused them.
- If targeted verification fails: fix it before making the next change.
- Full suite run only at final verification phase.

## Anti-Patterns

- Do not retry a failing command without reading the error.
- Do not add more code to fix an error you haven't diagnosed.
- Do not declare done with untested failure modes.
- Do not run the full suite in place of targeted verification mid-task.
