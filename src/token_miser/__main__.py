"""CLI entry point for token-miser."""

from __future__ import annotations

import argparse
import json
import os
import sys

from token_miser.backends import get_backend, parse_agents
from token_miser.checker import check_all_criteria
from token_miser.db import Run, get_run, get_runs, init_db, store_run
from token_miser.environment import setup_env
from token_miser.evaluator import score_quality
from token_miser.package_ref import list_packages, parse_package_ref, resolve_packages_dir
from token_miser.report import analyze, compare
from token_miser.task import load_task


def cmd_run(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    conn = init_db()
    packages_dir = getattr(args, "packages_dir", None)
    agents = parse_agents(getattr(args, "agent", None))
    try:
        specs = [args.baseline]
        if args.package:
            specs.append(args.package)
            if getattr(args, "order", "baseline-first") == "package-first":
                specs = [args.package, args.baseline]

        results = []
        for agent_name in agents:
            backend = get_backend(agent_name)
            backend_env = backend.load_env()
            for spec in specs:
                package_ref = parse_package_ref(spec, packages_dir=packages_dir)
                print(f"Running {backend.name}:{package_ref.name}...", file=sys.stderr)
                env = setup_env(task, package_ref, agent=backend.name)
                try:
                    bare = getattr(args, "bare", False)
                    model = getattr(args, "model", None)
                    if task.type == "sequential":
                        res = backend.run_sequential(
                            task.prompts,
                            env.home_dir,
                            env.workspace_dir,
                            timeout=args.timeout,
                            extra_env=backend_env,
                            bare=bare,
                            model=model,
                        )
                    else:
                        res = backend.run(
                            task.prompt,
                            env.home_dir,
                            env.workspace_dir,
                            timeout=args.timeout,
                            extra_env=backend_env,
                            bare=bare,
                            model=model,
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
                        agent=backend.name,
                        task_id=task.id,
                        package_name=package_ref.name,
                        loadout_name=package_ref.package_path.split("/")[-1] if package_ref.package_path else "",
                        model=backend.resolve_model(model),
                        wall_seconds=res.wall_seconds,
                        input_tokens=res.usage.input_tokens,
                        output_tokens=res.usage.output_tokens,
                        cache_read_tokens=res.usage.cache_read_input_tokens,
                        cache_write_tokens=res.usage.cache_creation_input_tokens,
                        reasoning_tokens=res.usage.reasoning_tokens,
                        total_cost_usd=res.total_cost_usd,
                        criteria_pass=passed,
                        criteria_total=total,
                        quality_scores=quality_json,
                        result=res.result,
                    )
                    run_id = store_run(conn, run)
                    results.append((backend.name, package_ref.name, run.model, res, passed, total, run_id))
                finally:
                    env.teardown()

        print("\n=== Run Summary ===")
        for agent_name, name, model_name, res, passed, total, run_id in results:
            print(
                f"Agent: {agent_name} | Package: {name} | Model: {model_name or '-'} | "
                f"Input: {res.usage.input_tokens:,} | Output: {res.usage.output_tokens:,} | "
                f"Cached: {res.usage.cache_read_input_tokens:,} | "
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

        print(
            f"{'ID':>4}  {'Agent':<8}  {'Task':<16}  {'Package':<20}  {'Tokens':>10}  "
            f"{'Wall':>8}  {'Cost':>12}  {'Criteria':>10}"
        )
        for r in runs:
            tokens = r.input_tokens + r.output_tokens
            wall = f"{r.wall_seconds:.1f}s" if r.wall_seconds > 0 else "-"
            criteria = f"{r.criteria_pass}/{r.criteria_total}" if r.criteria_total else "-"
            print(
                f"{r.id:>4}  {r.agent:<8}  {r.task_id:<16}  {r.package_name:<20}  {tokens:>10,}  "
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
        print(f"  Agent:      {run.agent}")
        print(f"  Task:       {run.task_id}")
        print(f"  Package:    {run.package_name}")
        print(f"  Model:      {run.model}")
        print(f"  Started:    {run.started_at}")
        print(f"  Wall time:  {run.wall_seconds:.1f}s")
        print(f"  Input:      {run.input_tokens:,} tokens")
        print(f"  Output:     {run.output_tokens:,} tokens")
        print(f"  Cached:     {run.cache_read_tokens:,} tokens")
        if run.reasoning_tokens:
            print(f"  Reasoning:  {run.reasoning_tokens:,} tokens")
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
            print(f"\n--- {run.agent.title()} Output ---")
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

    packages_dir = getattr(args, "packages_dir", None)
    package_path = args.package
    if package_path and "/" not in package_path and "\\" not in package_path:
        pkg = resolve_packages_dir(packages_dir) / package_path
        package_path = str(pkg)

    agents = parse_agents(getattr(args, "agent", None))
    exit_code = 0
    for agent_name in agents:
        output_dir = args.output
        if len(agents) > 1:
            output_dir = f"{args.output}-{agent_name}"
        exit_code = max(
            exit_code,
            run_tune(
                suite_name=args.suite,
                skip_baseline=args.skip_baseline,
                package_path=package_path,
                output_dir=output_dir,
                timeout=args.timeout,
                model=args.model,
                yes=args.yes,
                bare=args.bare,
                agent=agent_name,
            ),
        )
    return exit_code


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


def cmd_matrix(args: argparse.Namespace) -> int:
    from pathlib import Path

    from token_miser.db import init_db
    from token_miser.matrix import build_matrix, export_matrix_json

    conn = init_db()
    try:
        if args.json_out:
            path = export_matrix_json(args.suite, Path(args.json_out), conn)
            print(f"Matrix exported to {path}")
        else:
            print(build_matrix(args.suite, conn))
    finally:
        conn.close()
    return 0


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


def cmd_publish(args: argparse.Namespace) -> int:
    from pathlib import Path

    from token_miser.publish import generate_manifest_snippet, publish_package

    pkg_path = Path(args.package_dir)
    if not pkg_path.is_dir():
        print(f"ERROR: {args.package_dir} is not a directory", file=sys.stderr)
        return 1

    try:
        result = publish_package(
            pkg_path,
            args.repo,
            name=args.name,
            version=args.version,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Published {result['package_name']} v{result['version']}")
    print(f"Tag: {result['tag']}")
    print("\nKanon manifest snippet:")
    print(f"  {generate_manifest_snippet(result['package_name'], result['version'])}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    packages_dir = getattr(args, "packages_dir", None)
    resolved = resolve_packages_dir(packages_dir)
    names = list_packages(packages_dir)

    if not names:
        print(f"No packages found in {resolved}/")
        return 0

    print(f"Packages in {resolved}/:")
    for name in names:
        print(f"  {name}")
    return 0


def cmd_packages(args: argparse.Namespace) -> int:
    from pathlib import Path

    import yaml

    from token_miser.package_adapter import discover_kanon_packages

    # Check for .kanon file
    kanonenv = Path.cwd() / ".kanon"
    packages = discover_kanon_packages(kanonenv)

    if not packages:
        # Also check .packages/ directly
        packages_dir = Path.cwd() / ".packages"
        if packages_dir.is_dir():
            packages = sorted(p for p in packages_dir.iterdir() if p.is_dir() and (p / "manifest.yaml").exists())

    if not packages:
        print("No kanon packages found. Run 'kanon install' first, or check .packages/ directory.")
        return 0

    print(f"{'Package':<24} {'Version':<12} {'Description'}")
    print("-" * 70)
    for pkg_path in packages:
        try:
            manifest = yaml.safe_load((pkg_path / "manifest.yaml").read_text())
            name = manifest.get("name", pkg_path.name)
            version = manifest.get("version", "?")
            desc = manifest.get("description", "")[:40]
            print(f"  {name:<22} {version:<12} {desc}")
        except Exception:
            print(f"  {pkg_path.name:<22} (error reading manifest)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    from token_miser import __version__

    parser = argparse.ArgumentParser(prog="token-miser", description="Benchmark coding-agent configuration packages")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--packages-dir",
        default=None,
        help="Directory containing packages (default: $TOKEN_MISER_PACKAGES_DIR or ./packages)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run an experiment")
    p_run.add_argument("--task", required=True, help="Path to task YAML")
    p_run.add_argument("--baseline", required=True, help="Baseline spec ('vanilla' or package path)")
    p_run.add_argument("--package", default=None, help="Package path to benchmark")
    p_run.add_argument("--agent", default="claude", help="Agent backend: claude, codex, openai(alias), or both")
    p_run.add_argument(
        "--order",
        choices=("baseline-first", "package-first"),
        default="baseline-first",
        help="Execution order when both baseline and package are present",
    )
    p_run.add_argument(
        "--model",
        default=None,
        help="Model identifier (defaults by agent: sonnet for Claude, gpt-5.4 for Codex)",
    )
    p_run.add_argument("--timeout", type=int, default=600, help="Per-invocation timeout in seconds (default: 600)")
    p_run.add_argument("--bare", action="store_true", help="Skip hooks/plugins (cheaper, less realistic)")

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
    p_tune.add_argument("--agent", default="claude", help="Agent backend: claude, codex, openai(alias), or both")
    p_tune.add_argument("--model", default=None, help="Model identifier (defaults by agent)")
    p_tune.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    p_tune.add_argument("--bare", action="store_true", help="Skip hooks/plugins (cheaper, less realistic)")

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

    # matrix
    p_matrix = sub.add_parser("matrix", help="Cross-package comparison matrix")
    p_matrix.add_argument("--suite", default="axis", help="Suite name (default: axis)")
    p_matrix.add_argument("--json", dest="json_out", default=None, help="Export matrix as JSON to this path")

    # publish
    p_publish = sub.add_parser("publish", help="Publish a package to a git repo for kanon")
    p_publish.add_argument("package_dir", help="Path to the package directory")
    p_publish.add_argument("--repo", required=True, help="Target git repo path")
    p_publish.add_argument("--name", default=None, help="Package name (default: from manifest)")
    p_publish.add_argument("--version", default=None, help="Package version (default: from manifest)")

    # packages
    sub.add_parser("packages", help="List kanon-distributed packages")

    # list
    sub.add_parser("list", help="List available packages from packages directory")

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
        "publish": cmd_publish,
        "packages": cmd_packages,
        "suite": cmd_suite,
        "matrix": cmd_matrix,
        "digest": cmd_digest,
        "list": cmd_list,
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
