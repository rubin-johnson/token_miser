"""Recommendation engine for CLAUDE.md improvements based on benchmark results."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Callable

from token_miser.db import Run


@dataclass
class Recommendation:
    category: str
    title: str
    description: str
    claude_md_block: str
    confidence: float
    evidence: str


def _parse_quality_scores(raw: str) -> dict[str, float] | None:
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {k: float(v) for k, v in data.items()}
        if isinstance(data, list):
            return {item["dimension"]: float(item["score"]) for item in data if "dimension" in item}
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        pass
    return None


def _avg_quality(runs: list[Run]) -> float | None:
    all_scores: list[float] = []
    for run in runs:
        parsed = _parse_quality_scores(run.quality_scores)
        if parsed:
            all_scores.extend(parsed.values())
    if not all_scores:
        return None
    return sum(all_scores) / len(all_scores)


def rule_high_tokens_no_grep(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    if not runs:
        return None
    avg_total = sum(r.input_tokens + r.output_tokens for r in runs) / len(runs)
    if avg_total <= 40000:
        return None
    md_lower = current_claude_md.lower()
    if "grep" in md_lower or "glob" in md_lower:
        return None
    return Recommendation(
        category="token_efficiency",
        title="Add grep-first rule",
        description="High average token usage without grep/glob guidance. "
        "Instructing the agent to search before reading full files reduces token waste.",
        claude_md_block=(
            "## Token Efficiency\n"
            "- Use grep/glob before reading full files — never read a file when a search answers it\n"
            "- One tool call per step when possible; don't speculatively read files you might not need"
        ),
        confidence=0.9,
        evidence=f"avg total tokens: {avg_total:.0f} (threshold: 40000)",
    )


def rule_low_minimal_change(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    scores: list[float] = []
    for run in runs:
        parsed = _parse_quality_scores(run.quality_scores)
        if parsed and "minimal_change" in parsed:
            scores.append(parsed["minimal_change"])
    if not scores:
        return None
    avg = sum(scores) / len(scores)
    if avg >= 0.75:
        return None
    return Recommendation(
        category="quality",
        title="Enforce minimal-change discipline",
        description="Low minimal_change scores suggest the agent over-engineers or adds unnecessary changes.",
        claude_md_block=(
            "## Quality\n"
            "- Solve what was asked, not the generalized version; no side quests\n"
            "- Simple > clever; match existing project patterns"
        ),
        confidence=0.85,
        evidence=f"avg minimal_change score: {avg:.2f} (threshold: 0.75)",
    )


def rule_high_variance_feature_tasks(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    feat_runs = [r for r in runs if "feat" in r.task_id]
    if len(feat_runs) < 2:
        return None
    totals = [r.input_tokens + r.output_tokens for r in feat_runs]
    mean = sum(totals) / len(totals)
    if mean == 0:
        return None
    variance = sum((t - mean) ** 2 for t in totals) / len(totals)
    stdev = math.sqrt(variance)
    if stdev <= 0.5 * mean:
        return None
    return Recommendation(
        category="structure",
        title="Add planning discipline for features",
        description="High token variance on feature tasks suggests inconsistent approach. "
        "A structured planning step can reduce variability.",
        claude_md_block=(
            "## Planning\n"
            "- Before starting a feature, outline the approach in 3-5 bullet points\n"
            "- If 3+ tool calls without progress, stop and reassess"
        ),
        confidence=0.75,
        evidence=f"feature task token stdev: {stdev:.0f}, mean: {mean:.0f} (stdev/mean: {stdev / mean:.1%})",
    )


def rule_low_criteria_pass_rate(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    total_pass = sum(r.criteria_pass for r in runs)
    total_criteria = sum(r.criteria_total for r in runs)
    if total_criteria == 0:
        return None
    rate = total_pass / total_criteria
    if rate >= 0.85:
        return None
    return Recommendation(
        category="quality",
        title="Re-read requirement before done",
        description="Low criteria pass rate indicates the agent misses requirements.",
        claude_md_block=(
            "## Quality\n"
            "- Before marking done: re-read the requirement, test failure inputs, find the simpler way\n"
            "- No hardcoded returns, no over-mocking, no 'it works in my head' without execution"
        ),
        confidence=0.88,
        evidence=f"criteria pass rate: {rate:.1%} (threshold: 85%)",
    )


def rule_empty_claude_md(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    lines = current_claude_md.strip().splitlines()
    if len(lines) >= 10:
        return None
    return Recommendation(
        category="structure",
        title="Add baseline CLAUDE.md template",
        description="A minimal or empty CLAUDE.md provides no guidance to the agent.",
        claude_md_block=(
            "## How to Work\n"
            "- Lead with the answer, explain after\n"
            "- Never stop to ask 'shall I proceed?' — just proceed\n\n"
            "## Quality\n"
            "- Actually solve the problem — not the happy path\n"
            "- Before done: re-read the requirement\n\n"
            "## Token Efficiency\n"
            "- Use grep/glob before reading full files\n"
            "- One tool call per step when possible"
        ),
        confidence=0.95,
        evidence=f"CLAUDE.md has {len(lines)} lines (threshold: 10)",
    )


def rule_high_wall_low_quality(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    if not runs:
        return None
    avg_wall = sum(r.wall_seconds for r in runs) / len(runs)
    if avg_wall <= 120:
        return None
    avg_q = _avg_quality(runs)
    if avg_q is None:
        return None
    if avg_q >= 0.7:
        return None
    return Recommendation(
        category="token_efficiency",
        title="Stop and reassess on slow runs",
        description="High wall time combined with low quality suggests the agent is spinning. "
        "Adding a reassessment checkpoint helps.",
        claude_md_block=(
            "## Efficiency\n"
            "- If 3+ tool calls without progress, stop and reassess\n"
            "- Prefer parallel execution when tasks are independent"
        ),
        confidence=0.8,
        evidence=f"avg wall_seconds: {avg_wall:.0f}, avg quality: {avg_q:.2f}",
    )


def rule_high_output_ratio(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    """Fires when output tokens are disproportionately high relative to input."""
    if not runs:
        return None
    total_input = sum(r.input_tokens for r in runs)
    total_output = sum(r.output_tokens for r in runs)
    if total_input == 0:
        return None
    ratio = total_output / total_input
    if ratio <= 0.15:
        return None
    md_lower = current_claude_md.lower()
    if "no unsolicited summaries" in md_lower or "no preamble" in md_lower:
        return None
    return Recommendation(
        category="token_efficiency",
        title="Reduce output verbosity",
        description="High output-to-input token ratio suggests verbose responses. "
        "Output tokens cost 5x more than input tokens.",
        claude_md_block=(
            "## Output Efficiency\n"
            "- No unsolicited summaries, no trailing questions, no preamble\n"
            "- Lead with the answer, explain after\n"
            "- One tool call per step when possible"
        ),
        confidence=0.82,
        evidence=f"output/input ratio: {ratio:.2f} (threshold: 0.15)",
    )


def rule_no_parallel_guidance(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    """Fires when high wall time and no parallel execution guidance."""
    if not runs:
        return None
    avg_wall = sum(r.wall_seconds for r in runs) / len(runs)
    if avg_wall <= 90:
        return None
    md_lower = current_claude_md.lower()
    if "parallel" in md_lower:
        return None
    return Recommendation(
        category="token_efficiency",
        title="Add parallel execution guidance",
        description="High average wall time without parallel execution guidance. "
        "Independent tool calls can run concurrently.",
        claude_md_block=(
            "## Execution\n"
            "- Prefer parallel execution when dispatching agents or running independent tasks\n"
            "- Don't speculatively read files you might not need"
        ),
        confidence=0.72,
        evidence=f"avg wall_seconds: {avg_wall:.0f} (threshold: 90)",
    )


def rule_high_cache_miss(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    """Fires when cache read tokens are low relative to total input, suggesting repeated full reads."""
    if not runs:
        return None
    total_input = sum(r.input_tokens for r in runs)
    total_cache_read = sum(r.cache_read_tokens for r in runs)
    if total_input == 0:
        return None
    cache_rate = total_cache_read / (total_input + total_cache_read) if (total_input + total_cache_read) else 0
    if cache_rate >= 0.3:
        return None
    if len(runs) < 3:
        return None
    return Recommendation(
        category="token_efficiency",
        title="Improve context reuse",
        description="Low cache hit rate suggests the agent re-reads context on each tool call. "
        "Structuring prompts for cache-friendly patterns reduces cost.",
        claude_md_block=(
            "## Context Efficiency\n"
            "- Read a file once and remember its contents; don't re-read between tool calls\n"
            "- Batch related operations to avoid context thrashing"
        ),
        confidence=0.7,
        evidence=f"cache read rate: {cache_rate:.1%} (threshold: 30%)",
    )


def rule_excessive_tokens_per_criterion(runs: list[Run], current_claude_md: str) -> Recommendation | None:
    """Fires when token cost per passing criterion is very high."""
    total_tokens = sum(r.input_tokens + r.output_tokens for r in runs)
    total_pass = sum(r.criteria_pass for r in runs)
    if total_pass == 0:
        return None
    tokens_per_pass = total_tokens / total_pass
    if tokens_per_pass <= 5000:
        return None
    md_lower = current_claude_md.lower()
    if "simple > clever" in md_lower and "grep" in md_lower:
        return None
    return Recommendation(
        category="token_efficiency",
        title="Reduce tokens per successful criterion",
        description="High token expenditure per passing criterion suggests over-engineering or "
        "exploratory approaches where a direct approach would suffice.",
        claude_md_block=(
            "## Approach\n"
            "- Simple > clever; match existing project patterns\n"
            "- Solve what was asked, not the generalized version; no side quests\n"
            "- Use grep/glob before reading full files"
        ),
        confidence=0.78,
        evidence=f"tokens per passing criterion: {tokens_per_pass:.0f} (threshold: 5000)",
    )


RuleFunc = Callable[[list[Run], str], Recommendation | None]

ALL_RULES: list[RuleFunc] = [
    rule_high_tokens_no_grep,
    rule_low_minimal_change,
    rule_high_variance_feature_tasks,
    rule_low_criteria_pass_rate,
    rule_empty_claude_md,
    rule_high_wall_low_quality,
    rule_high_output_ratio,
    rule_no_parallel_guidance,
    rule_high_cache_miss,
    rule_excessive_tokens_per_criterion,
]


def analyze_results(runs: list[Run], current_claude_md: str) -> list[Recommendation]:
    results: list[Recommendation] = []
    for rule in ALL_RULES:
        rec = rule(runs, current_claude_md)
        if rec is not None:
            results.append(rec)
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
