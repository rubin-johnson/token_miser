# Depth Control

Explore breadth-first. State assumptions before searching. One deep dive per task.

## Assumption-Driven Search

Before searching any codebase:
1. State your assumption about structure: "Assuming: Python project, src/ layout, Flask app, tests in tests/."
2. Search matching your assumption first (e.g., `glob src/**/*.py`, `grep -r "app = Flask"`).
3. If 2+ searches return nothing, broaden the assumption and restate it.
4. After 3 failed assumptions, stop and ask rather than guessing further.

## Breadth-First Traversal

- First exploration: top-level directory listing only. Understand the shape before drilling.
- Identify which subdirectory is relevant before entering it.
- Enter one subdirectory per task. If the task genuinely spans multiple areas, split into subtasks.
- After any deep dive: return to top-level orientation before diving into a second area.

## Search Hierarchy

Stop at the first level that answers the question:
1. Top-level index / file tree
2. Glob for file pattern
3. Grep for symbol/string
4. Read specific line range
5. Read full file — only if unavoidable and file is small

Never skip levels. Never open a file to find something grep can locate.

## One Deep Dive Rule

- Per task: one sustained deep dive into one area of the codebase.
- If you find yourself needing to deeply explore a second unrelated area, that's a new task.
- Surface the finding from your first dive before starting a second.
