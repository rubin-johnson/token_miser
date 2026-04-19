"""Comparison and analysis reporting."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field

from token_miser.db import get_runs


@dataclass
class PackageStats:
    name: str
    run_count: int = 0
    avg_tokens: float = 0.0
    avg_cost: float = 0.0
    stdev_cost: float = 0.0
    median_cost: float = 0.0
    avg_wall: float = 0.0
    criteria_pass: int = 0
    criteria_total: int = 0
    quality_scores: dict[str, float] = field(default_factory=dict)


def _run_label(run) -> str:
    agent = getattr(run, "agent", "") or "claude"
    return f"{agent}:{run.package_name}"


def compare(task_id: str, conn: sqlite3.Connection) -> str:
    """Generate a comparison report for runs of a given task."""
    runs = get_runs(conn, task_id)
    if not runs:
        return f"No runs found for task {task_id!r}\n"

    # Group by package, preserving insertion order
    by_pkg: dict[str, list] = {}
    for run in runs:
        by_pkg.setdefault(_run_label(run), []).append(run)

    stats = [_calculate_package_stats(name, pkg_runs) for name, pkg_runs in by_pkg.items()]

    if len(stats) == 2:
        return _format_side_by_side(task_id, stats)
    return _format_stacked(task_id, stats)


def analyze(task_id: str, conn: sqlite3.Connection) -> str:
    """Generate statistical analysis for runs of a given task."""
    runs = get_runs(conn, task_id)
    if not runs:
        return f"No runs found for task {task_id!r}\n"

    by_pkg: dict[str, list] = {}
    for run in runs:
        by_pkg.setdefault(_run_label(run), []).append(run)

    stats = [_calculate_package_stats(name, pkg_runs) for name, pkg_runs in by_pkg.items()]
    stats.sort(key=lambda s: s.avg_cost)

    # Find baseline (vanilla if present, else cheapest)
    baseline = next((s for s in stats if s.name.endswith(":vanilla") or s.name == "vanilla"), stats[0])

    total_runs = sum(s.run_count for s in stats)
    lines = [f"Task: {task_id}  ({total_runs} runs across {len(stats)} packages)\n"]
    lines.append(
        f"{'Package':<20} {'Runs':>4}  {'Avg Cost':>10}  {'Stdev':>8}  {'Median':>8}  "
        f"{'Avg Tok':>10}  {'Criteria':>8}  {'vs baseline':>12}"
    )
    lines.append("-" * 90)

    for s in stats:
        criteria_rate = (s.criteria_pass / s.criteria_total * 100) if s.criteria_total else 0
        if s.name == baseline.name:
            delta_str = "(baseline)"
        elif baseline.avg_cost:
            delta = (s.avg_cost - baseline.avg_cost) / baseline.avg_cost * 100
            delta_str = f"{delta:+.1f}%"
        else:
            delta_str = "n/a"

        lines.append(
            f"{s.name:<20} {s.run_count:>4}  ${s.avg_cost:>9.3f}  ${s.stdev_cost:>7.3f}  ${s.median_cost:>7.3f}  "
            f"{_fmt_tokens(int(s.avg_tokens)):>10}  {criteria_rate:>7.1f}%  {delta_str:>12}"
        )

    return "\n".join(lines) + "\n"


def _calculate_package_stats(name: str, runs: list) -> PackageStats:
    if not runs:
        return PackageStats(name=name)
    n = len(runs)
    total_cost = sum(r.total_cost_usd for r in runs)
    total_tokens = sum(r.input_tokens + r.output_tokens for r in runs)
    total_wall = sum(r.wall_seconds for r in runs)
    total_pass = sum(r.criteria_pass for r in runs)
    total_criteria = sum(r.criteria_total for r in runs)

    avg_cost = total_cost / n
    costs = [r.total_cost_usd for r in runs]
    stdev = 0.0
    if n >= 2:
        variance = sum((c - avg_cost) ** 2 for c in costs) / (n - 1)
        stdev = math.sqrt(variance)
    sorted_costs = sorted(costs)
    mid = n // 2
    median = (sorted_costs[mid - 1] + sorted_costs[mid]) / 2 if n % 2 == 0 else sorted_costs[mid]

    # Aggregate quality scores
    quality: dict[str, list[float]] = {}
    for run in runs:
        if run.quality_scores and run.quality_scores != "{}":
            try:
                scores = json.loads(run.quality_scores)
                if isinstance(scores, list):
                    for s in scores:
                        quality.setdefault(s["dimension"], []).append(s["score"])
                elif isinstance(scores, dict):
                    for k, v in scores.items():
                        quality.setdefault(k, []).append(float(v))
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    avg_quality = {k: sum(v) / len(v) for k, v in quality.items()}

    return PackageStats(
        name=name,
        run_count=n,
        avg_tokens=total_tokens / n,
        avg_cost=avg_cost,
        stdev_cost=stdev,
        median_cost=median,
        avg_wall=total_wall / n,
        criteria_pass=total_pass,
        criteria_total=total_criteria,
        quality_scores=avg_quality,
    )


def _format_side_by_side(task_id: str, stats: list[PackageStats]) -> str:
    a, b = stats
    lines = [f"=== Compare: {task_id} ===\n"]

    def row(label: str, va: str, vb: str) -> str:
        return f"  {label:<18} {va:>14}  |  {vb:>14}"

    lines.append(row("", a.name, b.name))
    lines.append(row("Runs", str(a.run_count), str(b.run_count)))
    lines.append(row("Avg tokens", _fmt_tokens(int(a.avg_tokens)), _fmt_tokens(int(b.avg_tokens))))
    lines.append(row("Avg cost", f"${a.avg_cost:.4f}", f"${b.avg_cost:.4f}"))
    lines.append(row("Avg wall (s)", f"{a.avg_wall:.1f}", f"{b.avg_wall:.1f}"))

    ca = f"{a.criteria_pass}/{a.criteria_total}" if a.criteria_total else "-"
    cb = f"{b.criteria_pass}/{b.criteria_total}" if b.criteria_total else "-"
    lines.append(row("Criteria", ca, cb))

    # Quality scores
    all_dims = sorted(set(list(a.quality_scores.keys()) + list(b.quality_scores.keys())))
    for dim in all_dims:
        sa = f"{a.quality_scores.get(dim, 0):.2f}" if dim in a.quality_scores else "-"
        sb = f"{b.quality_scores.get(dim, 0):.2f}" if dim in b.quality_scores else "-"
        lines.append(row(f"Q: {dim}", sa, sb))

    return "\n".join(lines) + "\n"


def _format_stacked(task_id: str, stats: list[PackageStats]) -> str:
    lines = [f"=== Compare: {task_id} ({len(stats)} packages) ===\n"]
    for s in stats:
        criteria = f"{s.criteria_pass}/{s.criteria_total}" if s.criteria_total else "-"
        lines.append(f"  {s.name}")
        lines.append(
            f"    Runs: {s.run_count}  Tokens: {_fmt_tokens(int(s.avg_tokens))}  "
            f"Cost: ${s.avg_cost:.4f}  Wall: {s.avg_wall:.1f}s  Criteria: {criteria}"
        )
        if s.quality_scores:
            qs = "  ".join(f"{k}: {v:.2f}" for k, v in s.quality_scores.items())
            lines.append(f"    Quality: {qs}")
        lines.append("")
    return "\n".join(lines)


def _fmt_tokens(n: int) -> str:
    """Format an integer with comma separators."""
    return f"{n:,}"
