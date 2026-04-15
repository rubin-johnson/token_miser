"""CLI entry point for token-miser."""
from __future__ import annotations

import argparse
import json
import os
import sys

from token_miser.checker import check_all_criteria
from token_miser.db import Run, get_run, get_runs, init_db, store_run
from token_miser.environment import setup_env
from token_miser.evaluator import score_quality
from token_miser.executor import load_claude_env, run_claude, run_claude_sequential
from token_miser.package_ref import parse_package_ref
from token_miser.report import analyze, compare
from token_miser.task import load_task


def cmd_run(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    conn = init_db()
    claude_env = load_claude_env()
    try:
        specs = [args.baseline]
        if args.package:
            specs.append(args.package)

        results = []
        for spec in specs:
            package_ref = parse_package_ref(spec)
            print(f"Running package: {package_ref.name}...", file=sys.stderr)
            env = setup_env(task, package_ref)
            try:
                if task.type == "sequential":
                    res = run_claude_sequential(
                        task.prompts, env.home_dir, env.workspace_dir,
                        timeout=args.timeout, extra_env=claude_env,
                    )
                else:
                    res = run_claude(
                        task.prompt, env.home_dir, env.workspace_dir,
                        timeout=args.timeout, extra_env=claude_env,
                    )

                checks = check_all_criteria(task.success_criteria, env)
                passed = sum(1 for c in checks if c.passed)
                total = len(checks)

                quality_json = "{}"
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if api_key and task.quality_rubric:
                    try:
                        scores = score_quality(
                            task.prompt or task.prompts[-1], res.result, task.quality_rubric, api_key
                        )
                        quality_json = json.dumps(
                            [{"dimension": s.dimension, "score": s.score, "reason": s.reason} for s in scores]
                        )
                    except Exception as e:
                        print(f"WARNING: quality scoring failed: {e}", file=sys.stderr)

                run = Run(
                    task_id=task.id,
                    package_name=package_ref.name,
                    loadout_name=package_ref.package_path.split("/")[-1] if package_ref.package_path else "",
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
                results.append((package_ref.name, res, passed, total, run_id))
            finally:
                env.teardown()

        print("\n=== Run Summary ===")
        for name, res, passed, total, run_id in results:
            print(
                f"Package: {name} | Input: {res.usage.input_tokens:,} | Output: {res.usage.output_tokens:,} | "
                f"Cost: ${res.total_cost_usd:.6f} | Wall: {res.wall_seconds:.1f}s | "
                f"Criteria: {passed}/{total} | Run ID: {run_id}"
            )
        return 0
    finally:
        conn.close()


def cmd_compare(args: argparse.Namespace) -> int:
    conn = init_db()
    try:
        print(compare(args.task, conn))
        return 0
    finally:
        conn.close()


def cmd_analyze(args: argparse.Namespace) -> int:
    conn = init_db()
    try:
        print(analyze(args.task, conn))
        return 0
    finally:
        conn.close()


def cmd_history(args: argparse.Namespace) -> int:
    conn = init_db()
    try:
        runs = get_runs(conn)
        if not runs:
            print("No runs recorded.")
            return 0

        print(f"{'ID':>4}  {'Task':<16}  {'Package':<20}  {'Tokens':>10}  {'Wall':>8}  {'Cost':>12}  {'Criteria':>10}")
        for r in runs:
            tokens = r.input_tokens + r.output_tokens
            wall = f"{r.wall_seconds:.1f}s" if r.wall_seconds > 0 else "-"
            criteria = f"{r.criteria_pass}/{r.criteria_total}" if r.criteria_total else "-"
            print(
                f"{r.id:>4}  {r.task_id:<16}  {r.package_name:<20}  {tokens:>10,}  "
                f"{wall:>8}  ${r.total_cost_usd:>11.6f}  {criteria:>10}"
            )
        return 0
    finally:
        conn.close()


def cmd_show(args: argparse.Namespace) -> int:
    conn = init_db()
    try:
        run = get_run(conn, args.run_id)
        if not run:
            print(f"Run {args.run_id} not found.", file=sys.stderr)
            return 1

        print(f"Run #{run.id}")
        print(f"  Task:       {run.task_id}")
        print(f"  Package:    {run.package_name}")
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
            text = run.result
            if len(text) > 2000:
                text = text[:2000] + "\n... (truncated)"
            print(text)
        return 0
    finally:
        conn.close()


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
    try:
        print("Database initialized and migrations applied.")
        return 0
    finally:
        conn.close()


def cmd_tune(args: argparse.Namespace) -> int:
    from token_miser.tune import run_tune

    return run_tune(
        suite_name=args.suite,
        skip_baseline=args.skip_baseline,
        package_path=args.package,
        output_dir=args.output,
        timeout=args.timeout,
        model=args.model,
        yes=args.yes,
    )


def cmd_suite(args: argparse.Namespace) -> int:
    from pathlib import Path

    from token_miser.suite import list_suites, load_suite
    from token_miser.tune import _benchmarks_dir

    benchmarks = _benchmarks_dir()
    suites_dir = benchmarks / "suites"
    tasks_dir = benchmarks / "tasks"

    if args.suite_command == "list":
        names = list_suites(suites_dir)
        if not names:
            print("No suites found.")
            return 0
        for name in names:
            suite_file = suites_dir / f"{name}.yaml"
            try:
                suite = load_suite(suite_file, tasks_dir)
                print(f"  {name:<16} {len(suite.tasks)} tasks  {suite.description}")
            except Exception:
                print(f"  {name:<16} (error loading)")
        return 0

    elif args.suite_command == "validate":
        suite_name = args.suite or "standard"
        suite_file = suites_dir / f"{suite_name}.yaml"
        if not suite_file.exists():
            print(f"Suite not found: {suite_name}", file=sys.stderr)
            return 1
        try:
            suite = load_suite(suite_file, tasks_dir)
            print(f"Suite '{suite.name}' v{suite.version}: {len(suite.tasks)} tasks — valid")
            return 0
        except Exception as e:
            print(f"Validation failed: {e}", file=sys.stderr)
            return 1

    elif args.suite_command == "prep":
        from token_miser.repos import ensure_repo, load_repos_config

        suite_name = args.suite or "standard"
        suite_file = suites_dir / f"{suite_name}.yaml"
        if not suite_file.exists():
            print(f"Suite not found: {suite_name}", file=sys.stderr)
            return 1

        suite = load_suite(suite_file, tasks_dir)
        repos_yaml = benchmarks / "repos.yaml"
        if repos_yaml.exists():
            specs = load_repos_config(repos_yaml)
            cache_dir = Path.home() / ".token_miser" / "repo_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            needed = {t.repo_id for t in suite.tasks if t.repo_id}
            for repo_id in sorted(needed):
                if repo_id in specs:
                    print(f"  Preparing {repo_id}...", end=" ", flush=True)
                    try:
                        ensure_repo(specs[repo_id], cache_dir, benchmarks_dir=benchmarks)
                        print("ok")
                    except Exception as e:
                        print(f"error: {e}")
                else:
                    print(f"  {repo_id}: not found in repos.yaml", file=sys.stderr)
        print("Done.")
        return 0

    print(f"Unknown suite command: {args.suite_command}", file=sys.stderr)
    return 1


def cmd_digest(args: argparse.Namespace) -> int:
    from pathlib import Path

    from token_miser.digest import compare_digests, export_all, export_session, list_digests

    if args.digest_command == "export":
        conn = init_db()
        try:
            if args.all:
                paths = export_all(conn)
                for p in paths:
                    print(f"  Exported: {p}")
                print(f"{len(paths)} digests exported.")
            else:
                from token_miser.db import get_latest_tune_session
                session = get_latest_tune_session(conn)
                if not session:
                    print("No tune sessions found.", file=sys.stderr)
                    return 1
                path = export_session(conn, session.id)
                print(f"Exported: {path}")
            return 0
        finally:
            conn.close()

    elif args.digest_command == "history":
        paths = list_digests()
        if not paths:
            print("No digests found.")
            return 0
        for p in paths:
            print(f"  {p.name}")
        return 0

    elif args.digest_command == "compare":
        p1 = Path(args.digest1)
        p2 = Path(args.digest2)
        if not p1.exists() or not p2.exists():
            print("One or both digest files not found.", file=sys.stderr)
            return 1
        print(compare_digests(p1, p2))
        return 0

    print(f"Unknown digest command: {args.digest_command}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    from token_miser import __version__

    parser = argparse.ArgumentParser(prog="token-miser", description="Benchmark Claude Code configuration packages")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run an experiment")
    p_run.add_argument("--task", required=True, help="Path to task YAML")
    p_run.add_argument("--baseline", required=True, help="Baseline spec ('vanilla' or package path)")
    p_run.add_argument("--control", dest="baseline", help=argparse.SUPPRESS)
    p_run.add_argument("--package", default=None, help="Package path to benchmark")
    p_run.add_argument("--treatment", dest="package", help=argparse.SUPPRESS)
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

    # tune
    p_tune = sub.add_parser("tune", help="Guided efficiency optimization")
    p_tune.add_argument("--suite", default="standard", help="Benchmark suite name (default: standard)")
    p_tune.add_argument("--skip-baseline", action="store_true", help="Reuse last baseline")
    p_tune.add_argument("--package", default=None, help="Test a specific package path")
    p_tune.add_argument("--profile", dest="package", help=argparse.SUPPRESS)
    p_tune.add_argument("--output", default="tuned-package", help="Output dir for generated package")
    p_tune.add_argument("--timeout", type=int, default=300, help="Per-task timeout in seconds")
    p_tune.add_argument("--model", default="sonnet", help="Model identifier")
    p_tune.add_argument("--yes", action="store_true", help="Skip confirmation prompts")

    # suite
    p_suite = sub.add_parser("suite", help="Manage benchmark suites")
    suite_sub = p_suite.add_subparsers(dest="suite_command", required=True)
    suite_sub.add_parser("list", help="List available suites")
    p_suite_validate = suite_sub.add_parser("validate", help="Validate suite tasks")
    p_suite_validate.add_argument("--suite", default=None, help="Suite name")
    p_suite_prep = suite_sub.add_parser("prep", help="Pre-clone suite repos")
    p_suite_prep.add_argument("--suite", default=None, help="Suite name")

    # digest
    p_digest = sub.add_parser("digest", help="Export run data for git tracking")
    digest_sub = p_digest.add_subparsers(dest="digest_command", required=True)
    p_digest_export = digest_sub.add_parser("export", help="Export sessions to digest files")
    p_digest_export.add_argument("--all", action="store_true", help="Export all sessions")
    digest_sub.add_parser("history", help="Show digest timeline")
    p_digest_compare = digest_sub.add_parser("compare", help="Compare two digests")
    p_digest_compare.add_argument("digest1", help="First digest file")
    p_digest_compare.add_argument("digest2", help="Second digest file")

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
        "tune": cmd_tune,
        "suite": cmd_suite,
        "digest": cmd_digest,
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
