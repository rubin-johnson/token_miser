# Opportunistic Lazy

Reads are expensive. Never read the same content twice.

## No Re-Reads

- Track every file read in this session by name and line range.
- Before reading a file: has it been read already? If yes — reference it by name, not content. Do not re-fetch.
- Exception: re-read only if you have a specific reason to believe the file changed (e.g., you edited it via a tool, or another process was expected to modify it).

## Edit Without Re-Read

- After an edit: treat the change as known. Do not read the file again to confirm the edit was applied.
- If you need to verify correctness, run a test — not a re-read.

## Batch Mutations

- If you need to make multiple edits to one file: plan all edits before making the first.
- Execute all edits to that file before moving to a different file.
- Do not interleave reads and edits on the same file.

## Reference, Don't Repeat

- If a file's content is already in the conversation, reference it by filename + line range.
- Do not paste or re-fetch content that's already visible.
- If you need to show the user a piece of code, say "as read earlier in <file>:<line>" rather than re-reading.
