"""Cross-package matrix report from tune session data."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from token_miser.db import Run, init_db


@dataclass
class CellData:
    tokens: int = 0
    cost: float = 0.0
    wall: float = 0.0
    passed: bool = False
    criteria: str = ""
    error: bool = False


def _query_matrix_runs(conn: sqlite3.Connection, suite: str) -> list[dict]:
    rows = conn.execute("""
        SELECT r.task_id, r.package_name,
               r.input_tokens + r.output_tokens AS tokens,
               r.total_cost_usd AS cost,
               r.wall_seconds AS wall,
               r.criteria_pass, r.criteria_total,
               tr.phase, ts.id AS session_id, ts.tuned_package,
               r.started_at
        FROM runs r
        JOIN tune_runs tr ON r.id = tr.run_id
        JOIN tune_sessions ts ON tr.session_id = ts.id
        WHERE ts.suite_name = ?
        ORDER BY r.started_at DESC
    """, (suite,)).fetchall()
    return [dict(r) for r in rows]


def _latest_per_task_package(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Keep only the most recent run per (task_id, package_label) pair."""
    best: dict[tuple[str, str], dict] = {}
    for r in rows:
        if r["phase"] == "baseline":
            label = "baseline"
        else:
            label = r["tuned_package"] or r["package_name"]
        key = (r["task_id"], label)
        if key not in best:
            best[key] = r
    return best


def build_matrix(suite: str, conn: sqlite3.Connection | None = None) -> str:
    if conn is None:
        conn = init_db()

    rows = _query_matrix_runs(conn, suite)
    if not rows:
        return f"No tune data found for suite '{suite}'.\n"

    best = _latest_per_task_package(rows)

    tasks: list[str] = sorted({k[0] for k in best})
    packages: list[str] = sorted({k[1] for k in best})
    if "baseline" in packages:
        packages.remove("baseline")
        packages.insert(0, "baseline")

    col_w = 16
    task_w = 24
    header = f"{'task':<{task_w}}"
    for pkg in packages:
        header += f" {pkg:>{col_w}}"
    lines = [f"=== Matrix: {suite} ({len(tasks)} tasks x {len(packages)} packages) ===", ""]

    # Tokens table
    lines.append("TOKENS (input+output)")
    lines.append(header)
    lines.append("-" * len(header))
    for tid in tasks:
        row = f"{tid:<{task_w}}"
        for pkg in packages:
            cell = best.get((tid, pkg))
            if cell:
                row += f" {cell['tokens']:>{col_w},}"
            else:
                row += f" {'—':>{col_w}}"
        lines.append(row)

    # Cost table
    lines.append("")
    lines.append("COST (USD)")
    lines.append(header)
    lines.append("-" * len(header))
    for tid in tasks:
        row = f"{tid:<{task_w}}"
        for pkg in packages:
            cell = best.get((tid, pkg))
            if cell:
                row += f" ${cell['cost']:>{col_w - 1}.4f}"
            else:
                row += f" {'—':>{col_w}}"
        lines.append(row)

    # Pass/fail table
    lines.append("")
    lines.append("CRITERIA")
    lines.append(header)
    lines.append("-" * len(header))
    for tid in tasks:
        row = f"{tid:<{task_w}}"
        for pkg in packages:
            cell = best.get((tid, pkg))
            if cell:
                p, t = cell["criteria_pass"], cell["criteria_total"]
                mark = "PASS" if p == t else "FAIL"
                val = f"{mark} {p}/{t}"
                row += f" {val:>{col_w}}"
            else:
                row += f" {'—':>{col_w}}"
        lines.append(row)

    # Delta vs baseline table
    lines.append("")
    lines.append("TOKEN DELTA vs BASELINE")
    delta_header = f"{'task':<{task_w}}"
    non_baseline = [p for p in packages if p != "baseline"]
    for pkg in non_baseline:
        delta_header += f" {pkg:>{col_w}}"
    lines.append(delta_header)
    lines.append("-" * len(delta_header))
    for tid in tasks:
        row = f"{tid:<{task_w}}"
        base = best.get((tid, "baseline"))
        for pkg in non_baseline:
            cell = best.get((tid, pkg))
            if cell and base and base["tokens"]:
                delta = (cell["tokens"] - base["tokens"]) / base["tokens"] * 100
                row += f" {delta:>{col_w - 1}.1f}%"
            else:
                row += f" {'—':>{col_w}}"
        lines.append(row)

    # Totals row
    lines.append("")
    lines.append("TOTALS")
    totals_header = f"{'':>{task_w}}"
    for pkg in packages:
        totals_header += f" {pkg:>{col_w}}"
    lines.append(totals_header)
    lines.append("-" * len(totals_header))

    pkg_tokens: dict[str, int] = {}
    pkg_cost: dict[str, float] = {}
    pkg_pass: dict[str, int] = {}
    pkg_total: dict[str, int] = {}
    for pkg in packages:
        pkg_tokens[pkg] = sum(best[(tid, pkg)]["tokens"] for tid in tasks if (tid, pkg) in best)
        pkg_cost[pkg] = sum(best[(tid, pkg)]["cost"] for tid in tasks if (tid, pkg) in best)
        pkg_pass[pkg] = sum(best[(tid, pkg)]["criteria_pass"] for tid in tasks if (tid, pkg) in best)
        pkg_total[pkg] = sum(best[(tid, pkg)]["criteria_total"] for tid in tasks if (tid, pkg) in best)

    row_tok = f"{'tokens':<{task_w}}"
    row_cost = f"{'cost':<{task_w}}"
    row_rate = f"{'pass rate':<{task_w}}"
    for pkg in packages:
        row_tok += f" {pkg_tokens[pkg]:>{col_w},}"
        row_cost += f" ${pkg_cost[pkg]:>{col_w - 1}.4f}"
        rate = pkg_pass[pkg] / pkg_total[pkg] * 100 if pkg_total[pkg] else 0
        row_rate += f" {rate:>{col_w - 1}.1f}%"
    lines.append(row_tok)
    lines.append(row_cost)
    lines.append(row_rate)

    return "\n".join(lines) + "\n"


def export_matrix_json(suite: str, output: Path, conn: sqlite3.Connection | None = None) -> Path:
    if conn is None:
        conn = init_db()

    rows = _query_matrix_runs(conn, suite)
    if not rows:
        raise ValueError(f"No tune data found for suite '{suite}'")
    best = _latest_per_task_package(rows)

    tasks = sorted({k[0] for k in best})
    packages = sorted({k[1] for k in best})
    if "baseline" in packages:
        packages.remove("baseline")
        packages.insert(0, "baseline")

    data: dict[str, dict] = {}
    for tid in tasks:
        data[tid] = {}
        for pkg in packages:
            cell = best.get((tid, pkg))
            if cell:
                data[tid][pkg] = {
                    "tokens": cell["tokens"],
                    "cost": round(cell["cost"], 6),
                    "wall_seconds": round(cell["wall"], 1),
                    "criteria_pass": cell["criteria_pass"],
                    "criteria_total": cell["criteria_total"],
                }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as f:
        json.dump({"suite": suite, "packages": packages, "tasks": tasks, "matrix": data}, f, indent=2)
        f.write("\n")
    return output
