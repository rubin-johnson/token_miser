---
description: Token efficiency rules to minimize wasted context
---

# Efficiency

- Never re-read a file already in context
- Use line-range reads for large files
- Batch independent tool calls
- No explanatory text between tool calls unless reporting a finding
- Skip confirmation — just do it
