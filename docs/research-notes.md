# token_miser — Research Notes

## Prior Art Summary

### What exists

| Tool | What it does | Relevant? |
|------|-------------|-----------|
| [promptfoo](https://github.com/promptfoo/promptfoo) | YAML-driven prompt A/B testing; native Claude support; token cost tracking per run + aggregate; LLM-as-judge with 0-1 score + reason; custom Python providers | **Use this as experiment runner** |
| [DeepEval](https://deepeval.com) | Python-native quality eval; `TaskCompletion`, `StepEfficiency`, `ToolCorrectness` for agentic work; pytest integration; 0-1 score + reason on every metric | **Use this for quality evaluation** |
| [Braintrust AutoEvals](https://github.com/braintrustdata/autoevals) | Lighter LLM-as-judge; `Factuality`, `ClosedQA`, etc.; 0-1 score + rationale | Fallback to DeepEval |
| [Langfuse](https://langfuse.com) | Open-source observability; token cost tracking per request; prompt versioning | Candidate for token tracking layer |
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

### Internal GitHub repos (not yet accessed — GitHub not connected to EVO)

The following repos are noted for future investigation:
- `agentcore-evaluations-poc` — Bedrock AgentCore Evaluations PoC with Strands agent
- `caylent-evals` — evals datasets
- `simple-eval` — evaluation tools
- `llm-eval` — LLM evaluation framework
- `benchllm` — Python package to run benchmark tests for LLMs on Bedrock
- `BenchLLM-Stress-Test` — stress testing for LLMs
- `model-benchmark` — model benchmarking tools

**TODO**: Connect GitHub to EVO (`identity_connect provider=github features=[repos]`)
and review these repos before implementing.

### Internal documents to review

- [AI Evaluation Whitepaper](https://notion.so/caylent/206f1572580f804d8773f4a46c3b4834) (Marketing/Alliances)
- [Testing AI Systems Whitepaper](https://notion.so/caylent/1f2f1572580f8001b8d6c292555aa4f5) (Ryan Gross, June 2025)
- [7Signal GenAI Assessment](https://drive.google.com/file/d/15niKRG0iGSmyUk6giiV-PKBePfgp-x6P/view)
- [CloudZero Pricing Agent Performance Analysis](https://drive.google.com/file/d/1sE9VuiQz7RB-hCJ2YE1Z44_rHbS2-7uP/view)
- [CloudZero Benchmark Agent Documentation](https://drive.google.com/file/d/1YpLtTPVmq5oQckUxDuDpPAKGJWYnSpQn/view)

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

**On LLM testing methodology** (Sep 2023, #data):
Randall asked the team to create guidance around LLM testing. Metrics he wanted tracked:
- Accuracy, Recall, Precision
- Human Eval
- Performance (tokens/second)
- Context, Repetitiveness
- TopK/TopP/Temperature changes
- Single-shot vs few-shot performance
- Safety

**Battleground tool**: `battleground.caylent.com` — internal tool for real-time
model comparison (at least speed/price; "not the intelligence part"). Referenced as a
place Randall shows off prompt-flow and prompt catalogue demos.

**Key implication for token_miser**:
Randall is already thinking about this problem but doing it manually/informally.
token_miser could be something Caylent uses internally to inform their model guidance
to customers — not just a personal tool. Worth a conversation.

---

## Industry Benchmark Frameworks (for reference)

These are academic/research-grade benchmarks that could seed token_miser's benchmark suite:

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
| Experiment runner | promptfoo | Mature, native Claude, token tracking, LLM-as-judge, swappable |
| Quality evaluation | DeepEval | Agentic metrics, pytest integration, proven internally at Caylent |
| Experiment isolation | Docker | Clean env per run, loadout mounted at container start |
| Token tracking storage | SQLite | Already used by promptfoo; simple, portable |
| Config management | loadout (separate project) | See `/home/rujohnson/code/personal/loadout/` |
| Language | Python | Consistent with Caylent practice; DeepEval is Python-native |

---

## Open Questions

1. **GitHub not connected**: Need to review internal Caylent eval repos before
   implementing. See list above.
2. **Randall conversation**: Worth asking Randall directly if he'd use/contribute to
   token_miser. His overnight model testing is exactly what this automates.
3. **promptfoo multi-turn**: For synthetic workloads that need stateful multi-turn
   (Claude responding to its own previous outputs), need a custom Python provider.
   Verify this is feasible before committing to promptfoo.
4. **Claude Code non-interactive mode**: Experiments need to drive `claude` CLI without
   a TTY. Confirm `claude --print` or equivalent works for experiment automation.
