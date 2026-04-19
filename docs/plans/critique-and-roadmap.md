# token_miser — Critique & Roadmap

## Context

token_miser is a Go CLI that A/B tests Claude Code configurations by running identical tasks under different "arms" (vanilla vs. loadout bundle) and comparing token usage, cost, and quality. The MVP is complete: 12 Go source files, single-shot task execution, SQLite storage, LLM-as-judge quality scoring. This document is a candid assessment of the ideas, the implementation, and a roadmap for what comes next.

---

## Part 1: Critique of the Core Ideas

### What's genuinely novel

Token_miser occupies a real gap. The insight that **nobody benchmarks at the Claude Code configuration level** is correct and verified by the research:
- promptfoo, DeepEval, proprietary eval tools → measure prompt/model quality
- SWE-bench, AgentBench, TAU-Bench → measure task completion (pass/fail)
- Langfuse, LangSmith → observability, not evaluation
- None measure **agent efficiency** (tokens per unit of task completion under different configs)

The adjacent tool (loadout) managing config bundles makes the whole story coherent — loadout manages what you deploy, token_miser measures whether it was worth deploying.

### Conceptual blind spots

**1. Single-shot mode doesn't test what matters most.**
The MVP runs `claude --print` — a single, non-agentic invocation. But the research notes and the tool's own framing emphasize agentic behavior: tool calls, exploration strategy, context accumulation. In single-shot mode, a CLAUDE.md mostly just changes the system prompt. The token variance is small and uninteresting. The *entire value proposition* — that configuration affects how an agent navigates a task — only materializes in multi-turn mode, which is deferred. This is the most critical gap between the tool's pitch and its reality.

**2. The "loadout as treatment" framing is too narrow.**
Currently the only variable is "vanilla vs. one loadout bundle." But real teams want to test:
- Different models (Sonnet vs. Opus) on the same config
- Different MCP server configurations
- Different hook strategies
- A matrix of configs, not just A/B

Hardcoding to exactly 2 arms with the control/treatment metaphor limits this.

**3. Statistical validity is absent.**
A single run per arm tells you almost nothing. Claude's output has inherent variance (even with the same config). Without repeated runs and statistical significance testing, you can't distinguish signal from noise. The tool stores results for comparison but has no concept of sample size or confidence.

**4. The quality evaluator might not correlate with what users care about.**
Using Haiku to judge code quality on a 0-1 scale with 256 max tokens is likely to produce scores that cluster around 0.7-0.9 for anything remotely reasonable. The discriminative power between "good enough" and "excellent" is low. And evaluating dimensions independently misses interactions (e.g., high code quality but wrong structure = still bad).

**5. Portability problem.**
Task YAML files hardcode absolute paths (e.g. `repo: /path/to/my/repo`). This makes tasks non-portable across machines and non-shareable with teams — undermining the "version-controlled experiments" pitch.

---

## Part 2: Critique of the Implementation

### Critical (blocks real-world usage)

| Issue | Location | Impact |
|-------|----------|--------|
| **No execution timeout** | `executor.go:83` — `exec.CommandContext` uses `context.Background()` in practice | A Claude invocation can hang indefinitely. Real experiments need a timeout (e.g., 10 min). |
| **Quality scoring errors silently swallowed** | `cli.go:143` — `qualityScores, _ := evaluator.ScoreQuality(...)` | If the Anthropic API fails, you get zero quality data with no indication. Silent data loss. |
| **Hardcoded local paths in task YAML** | `tasks/synth-001.yaml` — absolute `repo:` paths | Tasks only work on one developer's machine. No way to run the included example tasks anywhere else. |
| **No repeat/multi-run support** | `cli.go` — arms run once each | Can't establish statistical significance. A single run is anecdotal, not evidence. |
| **readWorkspaceFiles reads 5 arbitrary files** | `evaluator.go:94-126` — WalkDir in filesystem order | The judge sees whatever 5 files come first alphabetically, not the files that matter. For a Python project, it might read `LICENSE` and `.gitignore` instead of `src/main.py`. |

### Important (degrades usefulness)

| Issue | Location | Impact |
|-------|----------|--------|
| **No stderr capture from Claude** | `executor.go:94` — `cmd.Output()` only captures stdout | If Claude fails, you lose diagnostic information. |
| **Report doesn't include quality scores** | `report.go:34-62` — only tokens/cost/criteria | Quality scores are stored in DB but never surfaced in comparison. Half the evaluation pipeline is invisible. |
| **No delta calculation in reports** | `report.go` | Reports show each arm's numbers but never compute the diff (e.g., "treatment used 23% fewer tokens"). Users must do math manually. |
| **Sequential arm execution** | `cli.go:109-113` | Arms run one after another. For experiments with many arms or long tasks, this is unnecessarily slow. Parallel execution is straightforward. |
| **No schema migrations** | `db.go:14-32` | Adding any column (e.g., claude_version, git_sha) requires manually recreating the DB. |
| **No run metadata** | `db.go` Run struct | Doesn't capture: Claude CLI version, token_miser version, OS, git SHA of token_miser itself. Makes results non-reproducible. |

### Minor (paper cuts)

| Issue | Location | Impact |
|-------|----------|--------|
| No README | root | No one can figure out what this is or how to use it without reading source |
| No CI/CD | root | No automated quality gates |
| No machine-readable output | `report.go`, `cli.go` | Can't pipe results to other tools or dashboards |
| No progress reporting | `cli.go` | Long-running experiments give no feedback |
| `tasksCmd` manual YAML extension check | `cli.go:264` | Fragile string slicing instead of `filepath.Ext()` |
| Command injection risk in checker | `checker.go` | Task YAML commands run in shell — safe only if YAML is trusted |

---

## Part 3: Improvements (by theme)

### Theme A: Make experiments trustworthy

1. **Add `--repeat N` flag** — Run each arm N times. Store all runs. Report averages, std dev, and a simple significance indicator (e.g., Cohen's d or Mann-Whitney U).
2. **Add execution timeout** — `context.WithTimeout` on Claude invocations, default 10 minutes, configurable via `--timeout`.
3. **Stop swallowing errors** — Propagate quality scoring errors. Log warnings for non-fatal failures rather than silently dropping data.
4. **Capture stderr** — Use `cmd.CombinedOutput()` or separate stderr pipe. Store stderr in the run record for diagnostics.
5. **Add run metadata** — Capture Claude CLI version (`claude --version`), token_miser git SHA, OS/arch, Go version. Store in a `run_metadata` JSON column.

### Theme B: Make the evaluator actually discriminating

1. **Smart file selection** — Instead of "first 5 files alphabetically," use heuristics: prioritize files matching patterns in the task prompt (e.g., if prompt mentions `pyproject.toml`, include it), prioritize files Claude created/modified (diff against starting commit), skip binary files.
2. **Increase judge context** — Bump max tokens to 512-1024. 256 forces terse reasoning that loses nuance.
3. **Upgrade judge model** — Allow configurable judge model. Haiku is fast/cheap but less discriminating. Sonnet is the sweet spot for most rubrics.
4. **Externalize rubrics to .md files** — Support `rubric_path: rubrics/code-quality.md` instead of inline YAML strings. Enables richer rubric descriptions with examples and anchoring.
5. **Add holistic evaluation** — After per-dimension scoring, run one final judge call with all dimensions + scores visible to produce an overall assessment and flag dimension conflicts.
6. **Adopt standard rubric dimensions** — Offer a default 7-attribute rubric (from simple-eval: Accuracy, Instruction Following, Format Compliance, Completeness, Clarity, Conciseness, Reasoning) as a starting template for new tasks.

### Theme C: Make tasks portable and experiments flexible

1. **Support relative/env-var repo paths** — Allow `repo: $LOADOUT_REPO` or `repo: ./fixtures/loadout` so tasks work across machines.
2. **Support N arms (not just 2)** — Replace `--control`/`--treatment` with `--arm vanilla --arm ./bundle-a --arm ./bundle-b`. Store arm order in results.
3. **Add `--matrix` mode** — Cross arms with models: `--arm vanilla --arm ./bundle --model sonnet --model opus` → 4 experiment cells.
4. **Add task templates** — Factor common patterns (Python scaffold, TypeScript refactor, bug fix) into reusable YAML templates.

### Theme D: Make results actionable

1. **Surface quality scores in reports** — Parse the quality_scores JSON and include per-dimension scores in comparison output.
2. **Add delta/diff rows** — Show percentage differences between arms: "treatment: -23% input tokens, +0.05 quality score."
3. **JSON/CSV export** — `token-miser compare --task X --format json` for pipeline integration.
4. **Trend visualization** — `token-miser trend --task X` showing metrics over time (even ASCII sparklines).
5. **HTML report generation** — For sharing results with non-CLI users.

### Theme E: The real unlock — multi-turn agentic mode

1. **Add `type: agentic` task type** — Instead of `--print`, run Claude as a full agent session. Capture the conversation log, all tool calls, and total token burn across turns.
2. **Measure exploration efficiency** — Track: number of tool calls, number of file reads, number of retries, number of dead ends (files read but not used in final output).
3. **Session replay** — Store the full Claude JSON conversation for post-hoc analysis.
4. **Cost-quality Pareto frontier** — With enough data points, plot the tradeoff between token cost and quality score to find the efficient frontier.

---

## Part 4: Detailed Roadmap

### Phase 1: Hardening (make the MVP actually usable)
*Goal: Someone other than the author can run a meaningful experiment.*

| # | Item | Files | Effort |
|---|------|-------|--------|
| 1.1 | Add `--repeat N` flag with multi-run execution | `cli.go`, `report.go` | M |
| 1.2 | Add `--timeout` flag with context deadline | `cli.go`, `executor.go` | S |
| 1.3 | Fix silent error swallowing in quality scoring | `cli.go` | S |
| 1.4 | Capture stderr from Claude invocations | `executor.go` | S |
| 1.5 | Make repo paths relative/env-var substitutable | `task.go`, `environment.go` | S |
| 1.6 | Surface quality scores in compare output | `report.go` | S |
| 1.7 | Add delta rows to comparison report | `report.go` | S |
| 1.8 | Add run metadata (claude version, git SHA, OS) | `db.go`, `executor.go`, `cli.go` | M |
| 1.9 | Write README with usage examples | `README.md` | S |
| 1.10 | Add CI pipeline (build + vet + test) | `.github/workflows/ci.yml` | S |

### Phase 2: Evaluator overhaul (make quality scores meaningful)
*Goal: Quality scores are discriminating enough to inform real decisions.*

| # | Item | Files | Effort |
|---|------|-------|--------|
| 2.1 | Smart file selection (prompt-aware, diff-aware) | `evaluator.go` | M |
| 2.2 | Configurable judge model (`--judge-model`) | `evaluator.go`, `cli.go` | S |
| 2.3 | Increase max tokens for judge responses | `evaluator.go` | S |
| 2.4 | Support external rubric .md files | `task.go`, `evaluator.go` | M |
| 2.5 | Add holistic evaluation pass | `evaluator.go` | M |
| 2.6 | Ship default 7-attribute rubric template | `rubrics/default-code.md` | S |
| 2.7 | Add statistical summary (std dev, significance) | `report.go` | M |

### Phase 3: Flexibility (support real-world experiment patterns)
*Goal: Teams can test the configurations they actually care about.*

| # | Item | Files | Effort |
|---|------|-------|--------|
| 3.1 | Support N arms (`--arm` repeatable flag) | `cli.go`, `report.go` | M |
| 3.2 | Add `--matrix` mode (arms x models) | `cli.go` | L |
| 3.3 | JSON/CSV export (`--format json\|csv`) | `report.go`, `cli.go` | M |
| 3.4 | Parallel arm execution | `cli.go` | M |
| 3.5 | Schema migration support | `db.go` | M |
| 3.6 | Add task templates / inheritance | `task.go` | M |
| 3.7 | Progress reporting during long runs | `cli.go` | S |

### Phase 4: The real product — agentic mode
*Goal: Measure what actually matters — how configuration affects agent behavior.*

| # | Item | Files | Effort |
|---|------|-------|--------|
| 4.1 | Add `type: agentic` task type (full Claude session) | `executor.go`, `task.go`, `cli.go` | L |
| 4.2 | Capture and store full conversation/tool-call logs | `executor.go`, `db.go` | L |
| 4.3 | Exploration efficiency metrics (tool calls, file reads, dead ends) | `executor.go`, `report.go` | L |
| 4.4 | Session diff viewer (compare how two arms explored differently) | new `internal/trace/` package | L |
| 4.5 | Cost-quality Pareto analysis | `report.go` | M |
| 4.6 | Multi-session experiments (context compaction recovery) | `executor.go`, `task.go` | XL |

### Phase 5: Ecosystem (if adoption warrants it)
*Goal: token_miser becomes a tool teams actually use, not a personal project.*

| # | Item | Effort |
|---|------|--------|
| 5.1 | Task library: curated set of portable benchmark tasks | M |
| 5.2 | HTML report generation for sharing | L |
| 5.3 | Integration with loadout's capture/apply lifecycle | M |
| 5.4 | Public leaderboard for loadout bundle efficiency | L |
| 5.5 | Overnight batch runner with notification (Randall's use case) | M |

---

## Sizing key
- **S** = a few hours, localized change
- **M** = 1-2 days, touches multiple files
- **L** = 3-5 days, new subsystem or significant refactor
- **XL** = 1-2 weeks, R&D component

## Verification

After each phase, the following should pass:
```bash
go build ./...
go vet ./...
go test ./...
```

Phase 1 should include at least one real experiment run (with actual Claude, not mocked) to validate the full pipeline end-to-end.

---

## Key insight: agent evaluation vs. prompt evaluation

- **Prompt evaluators** (promptfoo, simple-eval) = "which model/prompt answers best?"
- **token_miser** = agent-level evaluation → "which configuration makes the agent most efficient?"
- These are **different layers of the stack** with **shared grading patterns**
- The rubric/grader layer should converge (external .md rubrics, standard dimensions)
- The execution model, primary metrics, and variables under test are fundamentally different
- The strongest immediate adoption: externalize rubrics to .md files, adopt the 7-attribute rubric as a default template
