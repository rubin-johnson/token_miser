# token_miser — Research Notes

## Prior Art Summary

### What exists

| Tool | What it does | Relevant? |
|------|-------------|-----------|
| [promptfoo](https://github.com/promptfoo/promptfoo) | YAML-driven prompt A/B testing; native Claude support; token cost tracking per run + aggregate; LLM-as-judge with 0-1 score + reason | Reference for evaluation patterns; not used directly |
| [Caylent simple-eval](https://github.com/caylent/simple-eval) | DeepEval + Bedrock LLM-as-judge comparison framework; 7 evaluation attributes | Reference for quality rubric design |
| [Langfuse](https://langfuse.com) | Open-source observability; token cost tracking per request; prompt versioning | Not used; we track tokens natively via Claude JSON output |
| [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | CLAUDE.md template sharing community | Good for loadout bundle examples |

### What does NOT exist (our opportunity)

- No tool does "swap between full Claude config profiles" (CLAUDE.md + settings.json +
  hooks + MCP configs as a bundle) — this is **loadout**
- No tool benchmarks at the Claude Code configuration level (vs. prompt level) — this
  is **token_miser**

---

## Caylent Internal Resources

### Internal evaluation experience

Caylent has shipped DeepEval in multiple client projects:

**CloudZero (pricing agent)**:
- 33 test cases with DeepEval
- Tracked execution time, cost per run, step distribution
- Achieved cost reduction from $5–8 → $0.20–0.70 per run
- Key finding: step efficiency + model selection drove most of the savings

**7Signal (GenAI assessment)**:
- DeepEval + pytest in CI/CD pipeline
- LLM-as-a-Judge via Amazon Bedrock
- Multi-stage testing approach: run cheaper checks first, expensive LLM-judge only if deterministic passes
- Recommended: 60% automated (LLM-as-judge) / 40% manual review

**General internal best practices**:
- "Golden dataset" of 20–50 curated examples per use case
- Use anonymized production data to generate test cases
- CloudWatch GenAI Observability for trace collection → test case generation

### Internal GitHub repos (accessed via `gh` CLI)

| Repo | What it is | Relevance |
|------|-----------|-----------|
| `caylent/simple-eval` | DeepEval + Bedrock LLM-as-judge comparison | Quality rubric patterns |
| `caylent/caylent-evals` | Synthetic eval datasets for `caylent-iq` | Eval dataset structure |
| `caylent/agentcore-evaluations-poc` | Bedrock AgentCore Evaluations (TypeScript/CDK) | Different stack, low relevance |
| `caylent/llm-stt-benchmark` | Speech-to-text model benchmarking | Low relevance |
| `caylent/stt-model-benchmark` | STT model benchmarking | Low relevance |

### Internal documents to review

- [AI Evaluation Whitepaper](https://notion.so/caylent/206f1572580f804d8773f4a46c3b4834) (Marketing/Alliances)
- [Testing AI Systems Whitepaper](https://notion.so/caylent/1f2f1572580f8001b8d6c292555aa4f5) (Ryan Gross, June 2025)
- [7Signal GenAI Assessment](https://drive.google.com/file/d/15niKRG0iGSmyUk6giiV-PKBePfgp-x6P/view)
- [CloudZero Pricing Agent Performance Analysis](https://drive.google.com/file/d/1sE9VuiQz7RB-hCJ2YE1Z44_rHbS2-7uP/view)

---

## Randall Hunt's Perspective (CTO, from Slack)

Randall is doing informal empirical model evaluation — not yet systematic. Key signals:

**On benchmarks vs. real workloads** (Aug 2025, #sales):
> "The danger of benchmarks is that they don't always represent real customer workloads.
> We ran some experiments overnight and saw that the models had 'star fish' shaped
> knowledge. Deep in many areas but very weak in areas outside of the benchmarking set.
> It may have been 'overfit' to the benchmarking data."

**On evals** (same message):
> "This is why it is so important for customers to pursue evals! Evals, evals, evals,
> evals! That is how you measure a model on real world tasks."

**On tokens/cost** (responding to unit economics question):
> "Any customer hitting unit economic issues around token costs that are not as sensitive
> to outputs being 100% correct."

**On overnight testing** (Aug 2025, #generative-ai) — OpenAI OSS 120B evaluation:
- Ran empirical overnight tests hitting rate limits repeatedly
- Tested structured output, math/reasoning, code generation, benchmark recall
- Found model had memorized benchmark set (changing coefficients returned original answers)
- This is exactly the "benchmarks can lie" problem token_miser needs to guard against

**Battleground tool**: `battleground.caylent.com` — internal tool for real-time
model comparison (at least speed/price; "not the intelligence part").

**Key implication for token_miser**:
Randall is already thinking about this problem but doing it manually/informally.
token_miser could be something Caylent uses internally — worth a conversation.

---

## Industry Benchmark Frameworks (for reference)

- **τ-Bench (TAU-Bench)** — stateful evaluation for agents interacting with APIs
- **AgentBench** — 8 environments: OS, databases, web shopping, etc.
- **WebArena** — web-based agent navigation
- **GAIA** — general intelligence multi-step reasoning
- **ToolBench** — tool usage accuracy across thousands of API scenarios

None of these measure Claude Code configuration-level token efficiency. That's the gap.

---

## Technology Choices

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Go | Consistent with ralphael (same author); subprocess orchestration, CLI tools |
| Experiment runner | Custom (internal/executor) | Config-level comparison, not prompt comparison; simpler than promptfoo |
| Quality evaluation | LLM-as-judge via Anthropic Go SDK | Per-dimension 0-1 scores, same pattern as Caylent's simple-eval |
| Experiment isolation | HOME override (temp dirs) | Simpler than Docker; Claude reads `$HOME/.claude/` |
| Token tracking | Claude `--output-format json` | Native; no external observability needed |
| Storage | SQLite via `modernc.org/sqlite` | Pure Go, no cgo, portable |
| Config management | loadout (external tool) | Applies config bundles to experiment environments |

---

## Open Questions

1. **Randall conversation**: Worth asking Randall directly if he'd use/contribute to
   token_miser. His overnight model testing is exactly what this automates.
2. **Multi-session experiments**: Future task type measuring context compaction recovery —
   designed but deferred to post-MVP.
3. **Claude Code non-interactive mode**: Confirmed working via ralphael's runner.go
   pattern: `--print --dangerously-skip-permissions --output-format json`, strip
   `CLAUDECODE` from env, prompt via stdin.
