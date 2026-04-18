"""Tune workflow — guided efficiency optimization."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from token_miser.backends import get_backend
from token_miser.checker import check_all_criteria
from token_miser.db import (
    Run,
    TuneSession,
    create_tune_session,
    init_db,
    link_tune_run,
    store_run,
    update_tune_session,
)
from token_miser.environment import setup_env
from token_miser.evaluator import score_quality
from token_miser.package_adapter import create_package, pack_current_config, read_active_state
from token_miser.recommend import Recommendation, analyze_results
from token_miser.suite import BenchmarkTask, load_suite
from token_miser.task import Criterion, RubricDimension, Task
from token_miser.tune_builder import build_tuned_package


def _benchmarks_dir() -> Path:
    """Locate the benchmarks directory shipped with token_miser."""
    # Check relative to this file (installed package)
    pkg_dir = Path(__file__).parent
    candidates = [
        pkg_dir.parent.parent / "benchmarks",  # dev: src/token_miser/../../benchmarks
        pkg_dir / "benchmarks",                 # installed: token_miser/benchmarks
    ]
    for c in candidates:
        if c.is_dir():
            return c
    raise FileNotFoundError("Cannot locate benchmarks directory")


def _benchmark_task_to_task(bt: BenchmarkTask, repo_path: str) -> Task:
    """Convert a BenchmarkTask to a Task for the existing executor pipeline."""
    criteria = [
        Criterion(
            type=c.get("type", ""),
            paths=c.get("paths", []),
            command=c.get("command", ""),
            contains=c.get("contains", []),
        )
        for c in bt.success_criteria
    ]
    rubric = [
        RubricDimension(dimension=r["dimension"], prompt=r["prompt"])
        for r in bt.quality_rubric
    ]
    return Task(
        id=bt.id,
        name=bt.name,
        repo=repo_path,
        starting_commit=bt.starting_commit,
        prompt=bt.prompt,
        prompts=bt.prompts,
        type=bt.type,
        success_criteria=criteria,
        quality_rubric=rubric,
        repo_id=bt.repo_id,
        category=bt.category,
    )


def _capture_codex_baseline_files(codex_home: Path, fallback_claude_home: Path) -> dict[str, str]:
    current_text = ""
    for path in (codex_home / "AGENTS.md", fallback_claude_home / "CLAUDE.md"):
        if path.exists():
            current_text = path.read_text()
            break

    if not current_text:
        return {}
    return {
        "AGENTS.md": current_text,
        "CLAUDE.md": "@AGENTS.md\n",
    }


def _run_single_task(
    task: Task,
    package_path: Path | None,
    backend_name: str,
    model: str,
    timeout: int,
    conn: sqlite3.Connection,
    backend_env: dict[str, str] | None = None,
    bare: bool = False,
) -> Run:
    """Run a single benchmark task and store the result."""
    from token_miser.package_ref import PackageRef

    backend = get_backend(backend_name)
    if package_path:
        package_ref = PackageRef(name=package_path.name, package_path=str(package_path.resolve()))
    else:
        package_ref = PackageRef(name="vanilla")

    env = setup_env(task, package_ref, agent=backend.name)
    try:
        if task.type == "sequential":
            res = backend.run_sequential(
                task.prompts, env.home_dir, env.workspace_dir,
                timeout=timeout, extra_env=backend_env, bare=bare, model=model,
            )
        else:
            res = backend.run(
                task.prompt, env.home_dir, env.workspace_dir,
                timeout=timeout, extra_env=backend_env, bare=bare, model=model,
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
        run.id = run_id
        return run
    finally:
        env.teardown()


def _print_run_line(idx: int, total: int, task_id: str, run: Run) -> None:
    tokens = run.input_tokens + run.output_tokens
    status = "ok" if run.criteria_pass == run.criteria_total else "FAIL"
    criteria = f"{run.criteria_pass}/{run.criteria_total}"
    print(
        f"  [{idx}/{total}] {task_id:<24} {status:<4}  "
        f"{tokens:>8,} tokens  ${run.total_cost_usd:.4f}  "
        f"{run.wall_seconds:.1f}s  {criteria} criteria"
    )


def _print_summary(label: str, runs: list[Run]) -> None:
    total_tokens = sum(r.input_tokens + r.output_tokens for r in runs)
    total_cost = sum(r.total_cost_usd for r in runs)
    total_pass = sum(r.criteria_pass for r in runs)
    total_criteria = sum(r.criteria_total for r in runs)
    pass_rate = total_pass / total_criteria * 100 if total_criteria else 0
    print(f"\n{label}:")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Total cost:   ${total_cost:.4f}")
    print(f"  Pass rate:    {pass_rate:.1f}% ({total_pass}/{total_criteria})")


def _print_comparison(baseline_runs: list[Run], tuned_runs: list[Run]) -> None:
    b_tokens = sum(r.input_tokens + r.output_tokens for r in baseline_runs)
    t_tokens = sum(r.input_tokens + r.output_tokens for r in tuned_runs)
    b_cost = sum(r.total_cost_usd for r in baseline_runs)
    t_cost = sum(r.total_cost_usd for r in tuned_runs)
    b_pass = sum(r.criteria_pass for r in baseline_runs)
    b_total = sum(r.criteria_total for r in baseline_runs)
    t_pass = sum(r.criteria_pass for r in tuned_runs)
    t_total = sum(r.criteria_total for r in tuned_runs)

    token_delta = ((t_tokens - b_tokens) / b_tokens * 100) if b_tokens else 0
    cost_delta = ((t_cost - b_cost) / b_cost * 100) if b_cost else 0
    b_rate = b_pass / b_total * 100 if b_total else 0
    t_rate = t_pass / t_total * 100 if t_total else 0

    print("\n=== Tune Results ===\n")
    print(f"{'':28} {'Baseline':>14} {'Tuned':>14} {'Delta':>10}")
    print(f"  {'Total tokens':<24} {b_tokens:>14,} {t_tokens:>14,} {token_delta:>+9.1f}%")
    print(f"  {'Total cost':<24} ${b_cost:>13.4f} ${t_cost:>13.4f} {cost_delta:>+9.1f}%")
    print(f"  {'Pass rate':<24} {b_rate:>13.1f}% {t_rate:>13.1f}% {t_rate - b_rate:>+9.1f}pp")

    if b_cost > 0:
        b_ei = (b_pass / b_total) / b_cost if b_total else 0
        t_ei = (t_pass / t_total) / t_cost if t_total and t_cost else 0
        ei_delta = ((t_ei - b_ei) / b_ei * 100) if b_ei else 0
        print(f"  {'Efficiency Index':<24} {b_ei:>14.1f} {t_ei:>14.1f} {ei_delta:>+9.1f}%")


def run_tune(
    suite_name: str = "standard",
    skip_baseline: bool = False,
    package_path: str | None = None,
    output_dir: str = "tuned-package",
    timeout: int = 300,
    model: str | None = None,
    yes: bool = False,
    bare: bool = False,
    agent: str = "claude",
) -> int:
    """Execute the full tune workflow."""
    backend = get_backend(agent)
    benchmarks = _benchmarks_dir()
    suites_dir = benchmarks / "suites"
    tasks_dir = benchmarks / "tasks"

    suite_file = suites_dir / f"{suite_name}.yaml"
    if not suite_file.exists():
        print(f"ERROR: Suite not found: {suite_name}", file=sys.stderr)
        print(f"Available: {', '.join(p.stem for p in suites_dir.glob('*.yaml'))}", file=sys.stderr)
        return 1

    suite = load_suite(suite_file, tasks_dir)
    backend_env = backend.load_env()

    # Resolve repo_ids to local paths
    from token_miser.repos import ensure_repo, load_repos_config

    repos_yaml = benchmarks / "repos.yaml"
    repo_specs = load_repos_config(repos_yaml) if repos_yaml.exists() else {}
    cache_dir = Path.home() / ".token_miser" / "repo_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    repo_paths: dict[str, str] = {}
    for bt in suite.tasks:
        if bt.repo_id and bt.repo_id not in repo_paths:
            if bt.repo_id in repo_specs:
                path = ensure_repo(repo_specs[bt.repo_id], cache_dir, benchmarks_dir=benchmarks)
                repo_paths[bt.repo_id] = str(path)
            else:
                print(f"WARNING: repo_id '{bt.repo_id}' not in repos.yaml", file=sys.stderr)

    conn = init_db()
    baseline_dir: Path | None = None

    try:
        # Phase 1: Discovery
        if backend.name == "claude":
            target = Path.home() / ".claude"
            state = read_active_state(target) if target.exists() else None
            active_name = state.get("active", "none") if state else "none"
        else:
            target = Path.home() / ".codex"
            state = None
            active_name = "codex-default"

        print(f"Agent: {backend.name}")
        print(f"Current package: {active_name}")
        print(f"Suite: {suite.name} v{suite.version} ({len(suite.tasks)} tasks)")
        print(f"Estimated time: ~{len(suite.tasks) * 3} minutes per pass\n")

        if not yes:
            answer = input("Proceed with baseline benchmark? [Y/n] ").strip().lower()
            if answer and answer != "y":
                print("Aborted.")
                return 0

        # Capture current config as baseline package
        baseline_dir = Path(tempfile.mkdtemp(prefix="tune-baseline-"))
        if backend.name == "claude":
            pack_current_config(target, baseline_dir)
        else:
            files = _capture_codex_baseline_files(target, Path.home() / ".claude")
            create_package(
                name="codex-baseline",
                version="0.1.0",
                author="token-miser",
                description="Captured Codex baseline instructions",
                files=files,
                output_dir=baseline_dir,
            )
        baseline_pkg = baseline_dir

        current_instruction = ""
        for path in (target / "AGENTS.md", target / "CLAUDE.md", Path.home() / ".claude" / "CLAUDE.md"):
            if path.exists():
                current_instruction = path.read_text()
                break

        # Look up previous baseline BEFORE creating the new session
        from token_miser.db import get_latest_tune_session, get_tune_session_runs
        prev_session = get_latest_tune_session(conn, suite.name, backend.name) if skip_baseline else None

        # Create tune session
        session = TuneSession(
            agent=backend.name,
            suite_name=suite.name,
            suite_version=suite.version,
            baseline_package=active_name,
        )
        session_id = create_tune_session(conn, session)

        # Phase 2: Baseline benchmark
        baseline_runs: list[Run] = []
        if not skip_baseline:
            print(f"\nRunning baseline benchmarks ({active_name})...")
            for i, bt in enumerate(suite.tasks, 1):
                task = _benchmark_task_to_task(bt, repo_paths.get(bt.repo_id, ""))
                try:
                    run = _run_single_task(task, baseline_pkg, backend.name, model, timeout, conn, backend_env, bare)
                    link_tune_run(conn, session_id, run.id, "baseline")
                    baseline_runs.append(run)
                    _print_run_line(i, len(suite.tasks), bt.id, run)
                except Exception as e:
                    print(f"  [{i}/{len(suite.tasks)}] {bt.id:<24} ERROR: {e}", file=sys.stderr)

            _print_summary("Baseline", baseline_runs)
        else:
            if prev_session:
                baseline_runs = get_tune_session_runs(conn, prev_session.id, "baseline")
                print(f"\nReusing baseline from session #{prev_session.id} ({len(baseline_runs)} runs)")
            else:
                print("ERROR: No previous baseline found. Run without --skip-baseline first.", file=sys.stderr)
                return 1

        # Phase 3: Analysis and recommendations
        if package_path:
            # User supplied a specific package to test
            tuned_pkg = Path(package_path)
            recommendations: list[Recommendation] = []
            print(f"\nUsing supplied package: {package_path}")
        else:
            print("\nAnalyzing results...")
            recommendations = analyze_results(baseline_runs, current_instruction)

            if not recommendations:
                print("No recommendations — your config looks efficient already.")
                update_tune_session(conn, session_id, status="completed",
                                    completed_at=datetime.now(timezone.utc).isoformat())
                return 0

            print(f"\nRecommendations ({len(recommendations)}):")
            for r in recommendations:
                print(f"  [{r.confidence:.0%}] {r.title}")
                print(f"       {r.description}")

            # Phase 4: Build tuned package
            output = Path(output_dir)
            tuned_pkg = build_tuned_package(baseline_pkg, recommendations, output)
            print(f"\nGenerated tuned package at: {output}")

        update_tune_session(conn, session_id,
                            tuned_package=tuned_pkg.name,
                            recommendations_json=json.dumps(
                                [{"title": r.title, "category": r.category,
                                  "confidence": r.confidence} for r in recommendations]))

        if not yes:
            answer = input("\nRun benchmarks with tuned package? [Y/n] ").strip().lower()
            if answer and answer != "y":
                print("Skipping tuned benchmark. Package saved.")
                update_tune_session(conn, session_id, status="partial")
                return 0

        # Phase 5: Tuned benchmark
        print(f"\nRunning tuned benchmarks ({tuned_pkg.name})...")
        tuned_runs: list[Run] = []
        for i, bt in enumerate(suite.tasks, 1):
            task = _benchmark_task_to_task(bt, repo_paths.get(bt.repo_id, ""))
            try:
                run = _run_single_task(task, tuned_pkg, backend.name, model, timeout, conn, backend_env, bare)
                link_tune_run(conn, session_id, run.id, "tuned")
                tuned_runs.append(run)
                _print_run_line(i, len(suite.tasks), bt.id, run)
            except Exception as e:
                print(f"  [{i}/{len(suite.tasks)}] {bt.id:<24} ERROR: {e}", file=sys.stderr)

        _print_summary("Tuned", tuned_runs)

        # Phase 6: Comparison
        _print_comparison(baseline_runs, tuned_runs)

        update_tune_session(conn, session_id, status="completed",
                            completed_at=datetime.now(timezone.utc).isoformat())

        return 0

    finally:
        conn.close()
        if baseline_dir is not None:
            shutil.rmtree(baseline_dir, ignore_errors=True)
