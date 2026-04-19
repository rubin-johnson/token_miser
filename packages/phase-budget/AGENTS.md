# Phase Budget

Structure every task into three phases with hard tool-call budgets. If you exceed a phase budget, stop and re-plan before continuing.

## Phases

### Explore (budget: 10 tool calls)
- Locate files, understand structure, read relevant regions only.
- No full-file reads unless the file is under 50 lines.
- End this phase knowing: what files change, what functions are affected, what tests exist.

### Implement (budget: 15 tool calls)
- Make edits. One logical change per edit.
- Run targeted tests after each edit (not the full suite).
- No exploratory reads — you should know what you need.

### Verify (budget: 5 tool calls)
- Run full test suite. Run linter. Confirm the requirement is satisfied.
- Re-read the requirement. Check nothing was missed.
- Declare done only after verification passes.

## Budget Rules

- Track your call count per phase mentally or in comments.
- If you hit the budget without finishing: stop, write what you found/did, reassess the approach, restart that phase with a better plan.
- Budget overruns are a signal of poor planning, not a reason to keep going.
- If a phase takes 0 tool calls (you already know), skip it.

## Planning

- Before Explore begins, write a 3–5 step plan naming the specific files and changes.
- Update the plan when new information changes it — before acting on new information.
- No unplanned edits. If you discover a new change is needed, add it to the plan first.
