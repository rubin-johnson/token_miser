# Plan-Before-Code Workflow

## Planning

- Before any code change, write a numbered plan (3-7 steps)
- Each step names the specific file and what changes
- Execute steps in order, checking off each as completed
- If a step fails or reveals new info, update the plan before continuing
- No exploratory tool calls — know what you're looking for before reading a file

## Execution

- Run tests after each step, not just at the end
- If task takes >10 tool calls, pause and reassess the plan
- One logical change per edit — no bundling unrelated changes

## Efficiency

- Grep to locate, then read specific line ranges — never read full files speculatively
- No unsolicited refactoring outside the plan
