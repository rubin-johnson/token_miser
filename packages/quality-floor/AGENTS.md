# Quality Floor

Correctness over speed. Tokens are cheap; defects are not.

## Reading

- Before writing any code, read all relevant files in full. Understand before changing.
- If a file is referenced, read it — don't infer from context.
- Read error messages in full. Never guess at the cause.

## Reasoning

- Before making a change, state: what you're about to do, why, and what could go wrong.
- After making a change, state: what changed, what effect it has, what you verified.

## Code Quality

- Type annotations on all function signatures.
- Docstrings on all public functions: what it does, args, return, raises.
- Inline comments on non-obvious logic.
- Descriptive names. No abbreviations unless universally understood.
- Explicit over implicit at every decision point.

## Testing

- Happy path test.
- Error/exception test.
- Edge case tests: empty, zero, max, None, concurrent access.
- Integration test if the change touches multiple components.
- 100% branch coverage on new code.

## Verification

- Re-read the full requirement before declaring done.
- Verify every acceptance criterion explicitly — don't assume.
- Run full test suite + linter + type checker.
- If anything is unverified, state it explicitly rather than omitting it.
