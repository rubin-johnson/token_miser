"""CLI entry point for token-miser."""
from __future__ import annotations

import argparse
import json
import os
import sys

from token_miser.arm import parse_arm
from token_miser.checker import check_all_criteria
from token_miser.db import Run, get_run, get_runs, init_db, store_run
from token_miser.environment import setup_env
from token_miser.evaluator import score_quality
from token_miser.executor import run_claude, run_claude_sequential
from token_miser.report import analyze, compare
from token_miser.task import load_task


def cmd_run(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    conn = init_db()

    specs = []
    if args.control:
        specs.append(args.control)
    if args.treatment:
        specs.append(args.treatment)
    if not specs:
        print("ERROR: at least --control is required", file=sys.stderr)
        return 1

    results = []
    for spec in specs:
        arm = parse_arm(spec)
        print(f"Running arm: {arm.name}...", file=sys.stderr)
        env = setup_env(task, arm)
        try:
            if task.type == "sequential":
                res = run_claude_sequential(task.prompts, env.home_dir, env.workspace_dir, timeout=args.timeout)
            else:
                res = run_claude(task.prompt, env.home_dir, env.workspace_dir, timeout=args.timeout)

            checks = check_all_criteria(task.success_criteria, env)
            passed = sum(1 for c in checks if c.passed)
            total = len(checks)

            quality_json = "{}"
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key and task.quality_rubric:
                try:
                    scores = score_quality(task.prompt or task.prompts[-1], res.result, task.quality_rubric, api_key)
                    quality_json = json.dumps(
                        [{"dimension": s.dimension, "score": s.score, "reason": s.reason} for s in scores]
                    )
                except Exception as e:
                    print(f"WARNING: quality scoring failed: {e}", file=sys.stderr)

            run = Run(
                task_id=task.id,
                arm=arm.name,
                loadout_name=arm.name,
                model=args.model,
                wall_seconds=res.wall_seconds,
                input_tokens=res.usage.input_tokens,
                output_tokens=res.usage.output_tokens,
                cache_read_tokens=res.usage.cache_read_input_tokens,
                cache_write_tokens=res.usage.cache_creation_input_tokens,
                total_cost_usd=res.total_cost_usd,
                criteria_pass=passed,
                criteria_total=total,
                quality_scores=quality_json,
                result=res.result,
            )
            run_id = store_run(conn, run)
            results.append((arm.name, res, passed, total, run_id))
        finally:
            env.teardown()

    print("\n=== Run Summary ===")
    for name, res, passed, total, run_id in results:
        print(
            f"Arm: {name} | Input: {res.usage.input_tokens:,} | Output: {res.usage.output_tokens:,} | "
            f"Cost: ${res.total_cost_usd:.6f} | Wall: {res.wall_seconds:.1f}s | "
            f"Criteria: {passed}/{total} | Run ID: {run_id}"
        )

    conn.close()
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    conn = init_db()
    print(compare(args.task, conn))
    conn.close()
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    conn = init_db()
    print(analyze(args.task, conn))
    conn.close()
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    conn = init_db()
    runs = get_runs(conn)
    if not runs:
        print("No runs recorded.")
        conn.close()
        return 0

    print(f"{'ID':>4}  {'Task':<16}  {'Arm':<20}  {'Tokens':>10}  {'Wall':>8}  {'Cost':>12}  {'Criteria':>10}")
    for r in runs:
        tokens = r.input_tokens + r.output_tokens
        wall = f"{r.wall_seconds:.1f}s" if r.wall_seconds > 0 else "-"
        criteria = f"{r.criteria_pass}/{r.criteria_total}" if r.criteria_total else "-"
        print(
            f"{r.id:>4}  {r.task_id:<16}  {r.arm:<20}  {tokens:>10,}  "
            f"{wall:>8}  ${r.total_cost_usd:>11.6f}  {criteria:>10}"
        )

    conn.close()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    conn = init_db()
    run = get_run(conn, args.run_id)
    if not run:
        print(f"Run {args.run_id} not found.", file=sys.stderr)
        conn.close()
        return 1

    print(f"Run #{run.id}")
    print(f"  Task:       {run.task_id}")
    print(f"  Arm:        {run.arm}")
    print(f"  Model:      {run.model}")
    print(f"  Started:    {run.started_at}")
    print(f"  Wall time:  {run.wall_seconds:.1f}s")
    print(f"  Input:      {run.input_tokens:,} tokens")
    print(f"  Output:     {run.output_tokens:,} tokens")
    print(f"  Cost:       ${run.total_cost_usd:.6f}")
    print(f"  Criteria:   {run.criteria_pass}/{run.criteria_total}")

    if run.quality_scores and run.quality_scores != "{}":
        print("  Quality:")
        try:
            scores = json.loads(run.quality_scores)
            if isinstance(scores, list):
                for s in scores:
                    print(f"    {s['dimension']}: {s['score']:.2f} — {s.get('reason', '')}")
            elif isinstance(scores, dict):
                for k, v in scores.items():
                    print(f"    {k}: {v}")
        except json.JSONDecodeError:
            print(f"    (unparseable: {run.quality_scores})")

    if run.result:
        print("\n--- Claude Output ---")
        # Truncate very long output
        text = run.result
        if len(text) > 2000:
            text = text[:2000] + "\n... (truncated)"
        print(text)

    conn.close()
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    from pathlib import Path

    task_dir = Path(args.dir)
    if not task_dir.is_dir():
        print(f"ERROR: {args.dir} is not a directory", file=sys.stderr)
        return 1

    for f in sorted(task_dir.glob("*.yaml")):
        try:
            t = load_task(f)
            print(f"  {t.id:<20} {t.name}")
        except Exception as e:
            print(f"  {f.name:<20} (error: {e})", file=sys.stderr)
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    conn = init_db()
    print("Database initialized and migrations applied.")
    conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    from token_miser import __version__

    parser = argparse.ArgumentParser(prog="token-miser", description="A/B test Claude Code configurations")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run an experiment")
    p_run.add_argument("--task", required=True, help="Path to task YAML")
    p_run.add_argument("--control", required=True, help="Control arm spec ('vanilla' or loadout path)")
    p_run.add_argument("--treatment", default=None, help="Treatment arm spec (loadout path)")
    p_run.add_argument("--model", default="sonnet", help="Model identifier (default: sonnet)")
    p_run.add_argument("--timeout", type=int, default=600, help="Per-invocation timeout in seconds (default: 600)")

    # compare
    p_compare = sub.add_parser("compare", help="Compare runs for a task")
    p_compare.add_argument("--task", required=True, help="Task ID")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Statistical analysis for a task")
    p_analyze.add_argument("--task", required=True, help="Task ID")

    # history
    sub.add_parser("history", help="List all runs")

    # show
    p_show = sub.add_parser("show", help="Show details for a run")
    p_show.add_argument("run_id", type=int, help="Run ID")

    # tasks
    p_tasks = sub.add_parser("tasks", help="List task YAML files")
    p_tasks.add_argument("--dir", default="tasks", help="Directory containing task files")

    # migrate
    sub.add_parser("migrate", help="Initialize/migrate database")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "run": cmd_run,
        "compare": cmd_compare,
        "analyze": cmd_analyze,
        "history": cmd_history,
        "show": cmd_show,
        "tasks": cmd_tasks,
        "migrate": cmd_migrate,
    }

    try:
        sys.exit(handlers[args.command](args))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
