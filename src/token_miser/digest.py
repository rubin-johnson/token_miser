"""Digest export — git-trackable JSON summaries of tune sessions."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from token_miser.db import (
    Run,
    get_tune_session,
    get_tune_session_runs,
)


def _digest_dir() -> Path:
    return Path(".token_miser") / "digests"


def _summarize_runs(runs: list[Run]) -> dict:
    total_tokens = sum(r.input_tokens + r.output_tokens for r in runs)
    total_cost = sum(r.total_cost_usd for r in runs)
    total_pass = sum(r.criteria_pass for r in runs)
    total_criteria = sum(r.criteria_total for r in runs)
    pass_rate = total_pass / total_criteria if total_criteria else 0
    return {
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
        "criteria_pass": total_pass,
        "criteria_total": total_criteria,
        "pass_rate": round(pass_rate, 4),
        "run_count": len(runs),
    }


def _run_digest(run: Run) -> dict:
    return {
        "task_id": run.task_id,
        "package": run.package_name,
        "tokens": run.input_tokens + run.output_tokens,
        "cost": round(run.total_cost_usd, 6),
        "wall_seconds": round(run.wall_seconds, 1),
        "criteria": f"{run.criteria_pass}/{run.criteria_total}",
    }


def export_session(conn: sqlite3.Connection, session_id: int, output_dir: Path | None = None) -> Path:
    """Export a tune session as a JSON digest file."""
    session = get_tune_session(conn, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    baseline_runs = get_tune_session_runs(conn, session_id, "baseline")
    tuned_runs = get_tune_session_runs(conn, session_id, "tuned")

    baseline_summary = _summarize_runs(baseline_runs)
    tuned_summary = _summarize_runs(tuned_runs) if tuned_runs else {}

    token_reduction = 0.0
    if baseline_summary["total_tokens"] and tuned_summary.get("total_tokens"):
        token_reduction = round(
            (1 - tuned_summary["total_tokens"] / baseline_summary["total_tokens"]) * 100, 1
        )

    digest = {
        "type": "tune_session",
        "session_id": session.id,
        "suite": session.suite_name,
        "suite_version": session.suite_version,
        "timestamp": session.started_at,
        "baseline_package": session.baseline_package,
        "tuned_package": session.tuned_package or "",
        "status": session.status,
        "summary": {
            "baseline": baseline_summary,
            "tuned": tuned_summary,
            "token_reduction_pct": token_reduction,
        },
        "baseline_runs": [_run_digest(r) for r in baseline_runs],
        "tuned_runs": [_run_digest(r) for r in tuned_runs],
    }

    if session.recommendations_json:
        try:
            digest["recommendations"] = json.loads(session.recommendations_json)
        except json.JSONDecodeError:
            pass

    dest = output_dir or _digest_dir()
    dest.mkdir(parents=True, exist_ok=True)

    ts = session.started_at.replace(":", "-").replace("+", "_") if session.started_at else "unknown"
    filename = f"{ts}_{session.suite_name}.json"
    filepath = dest / filename

    with filepath.open("w") as f:
        json.dump(digest, f, indent=2)
        f.write("\n")

    return filepath


def export_all(conn: sqlite3.Connection, output_dir: Path | None = None) -> list[Path]:
    """Export all tune sessions as digest files."""
    rows = conn.execute("SELECT id FROM tune_sessions ORDER BY started_at").fetchall()
    paths = []
    for row in rows:
        try:
            paths.append(export_session(conn, row["id"], output_dir))
        except Exception:
            pass
    return paths


def list_digests(digest_dir: Path | None = None) -> list[Path]:
    """List all digest files."""
    d = digest_dir or _digest_dir()
    if not d.is_dir():
        return []
    return sorted(d.glob("*.json"))


def compare_digests(path1: Path, path2: Path) -> str:
    """Compare two digest files and return a formatted comparison."""
    d1 = json.loads(path1.read_text())
    d2 = json.loads(path2.read_text())

    lines = [
        f"Comparing: {path1.name} vs {path2.name}",
        "",
        f"{'':28} {'Session 1':>14} {'Session 2':>14}",
        f"  {'Suite':<24} {d1['suite']:>14} {d2['suite']:>14}",
        f"  {'Baseline package':<24} {d1['baseline_package']:>14} {d2['baseline_package']:>14}",
    ]

    s1 = d1.get("summary", {}).get("baseline", {})
    s2 = d2.get("summary", {}).get("baseline", {})

    if s1 and s2:
        lines.append("")
        lines.append("  Baseline:")
        lines.append(f"    {'Tokens':<22} {s1.get('total_tokens', 0):>14,} {s2.get('total_tokens', 0):>14,}")
        lines.append(f"    {'Cost':<22} ${s1.get('total_cost', 0):>13.4f} ${s2.get('total_cost', 0):>13.4f}")

    t1 = d1.get("summary", {}).get("tuned", {})
    t2 = d2.get("summary", {}).get("tuned", {})

    if t1 and t2:
        lines.append("")
        lines.append("  Tuned:")
        lines.append(f"    {'Tokens':<22} {t1.get('total_tokens', 0):>14,} {t2.get('total_tokens', 0):>14,}")
        lines.append(f"    {'Cost':<22} ${t1.get('total_cost', 0):>13.4f} ${t2.get('total_cost', 0):>13.4f}")

    r1 = d1.get("summary", {}).get("token_reduction_pct", 0)
    r2 = d2.get("summary", {}).get("token_reduction_pct", 0)
    lines.append("")
    lines.append(f"  {'Token reduction':<24} {r1:>13.1f}% {r2:>13.1f}%")

    return "\n".join(lines)
