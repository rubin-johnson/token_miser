# Minimal WIP

Build the smallest thing that satisfies the requirement. Nothing more.

## Minimum Viable Change

Before writing any code:
1. Re-read the requirement exactly as stated.
2. Identify the single smallest code change that satisfies it.
3. Write only that change.

If you find yourself adding error handling not required, refactoring surrounding code, adding helpers "for later," or generalizing a specific case — stop. That is out of scope.

## No Side Quests

- If you notice a bug adjacent to your task: note it in a comment or tell the user. Do not fix it.
- If you see an abstraction opportunity: note it. Do not apply it.
- If a test is missing for existing code: note it. Do not write it.
- Scope is what was asked for, not the ideal state of the codebase.

## Done Test

After writing code, apply this test:
- Does it satisfy the requirement? If no, it's incomplete.
- Does it do anything the requirement doesn't ask for? If yes, remove it.
- Is there a simpler version that also satisfies the requirement? If yes, use that.

## Code Style

- No comments unless the logic is non-obvious.
- No type annotations beyond what's needed for the code to work.
- No docstrings on private functions.
- No error handling for conditions that can't occur given your caller's contract.
