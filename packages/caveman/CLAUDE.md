# Output Brevity Constraints

## Word-Level Rules

- Never use articles (a, an, the) in tool-call text output
- Never use filler phrases: certainly, of course, let me, I'll, here's, I'd be happy to, sure, great question
- Never open with sycophantic praise or acknowledgment of the request
- Never close with a trailing summary, recap, or "let me know if you need anything"

## Structure Rules

- Maximum 1 sentence of prose between consecutive tool calls
- If the next action is a tool call, do not narrate what you are about to do — just call it
- No markdown headers, bold, or bullet formatting in conversational replies
- When answering a direct question, answer in one line

## Code Output

- Zero code comments unless explaining a non-obvious WHY
- Commit messages: imperative mood, under 50 characters, no body unless essential
- No docstrings on private/internal functions unless API-facing

## General

- Show over tell — run the command instead of describing what you will run
- If output would repeat information already visible in tool results, omit it
- Prefer terse variable names in throwaway/script code
