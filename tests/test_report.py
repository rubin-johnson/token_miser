"""Tests for report module."""

import json

from token_miser.db import Run, init_db, store_run
from token_miser.report import analyze, compare


def _setup_db(tmp_path, runs: list[Run]):
    conn = init_db(str(tmp_path / "test.db"))
    for run in runs:
        store_run(conn, run)
    return conn


def test_compare_no_runs(tmp_path):
    conn = _setup_db(tmp_path, [])
    result = compare("nonexistent", conn)
    assert "No runs found" in result
    conn.close()


def test_compare_two_packages(tmp_path):
    runs = [
        Run(task_id="t1", package_name="vanilla", input_tokens=100, output_tokens=50, total_cost_usd=0.01),
        Run(task_id="t1", package_name="package-b", input_tokens=80, output_tokens=40, total_cost_usd=0.008),
    ]
    conn = _setup_db(tmp_path, runs)
    result = compare("t1", conn)
    assert "vanilla" in result
    assert "package-b" in result
    assert "|" in result  # side-by-side format
    conn.close()


def test_compare_three_packages(tmp_path):
    runs = [
        Run(task_id="t1", package_name="a", total_cost_usd=0.01),
        Run(task_id="t1", package_name="b", total_cost_usd=0.02),
        Run(task_id="t1", package_name="c", total_cost_usd=0.03),
    ]
    conn = _setup_db(tmp_path, runs)
    result = compare("t1", conn)
    assert "a" in result
    assert "b" in result
    assert "c" in result
    conn.close()


def test_analyze_no_runs(tmp_path):
    conn = _setup_db(tmp_path, [])
    result = analyze("nonexistent", conn)
    assert "No runs found" in result
    conn.close()


def test_analyze_with_runs(tmp_path):
    runs = [
        Run(
            task_id="t1",
            package_name="vanilla",
            input_tokens=100,
            output_tokens=50,
            total_cost_usd=0.01,
            criteria_pass=3,
            criteria_total=5,
        ),
        Run(
            task_id="t1",
            package_name="vanilla",
            input_tokens=120,
            output_tokens=60,
            total_cost_usd=0.012,
            criteria_pass=4,
            criteria_total=5,
        ),
        Run(
            task_id="t1",
            package_name="package-b",
            input_tokens=80,
            output_tokens=40,
            total_cost_usd=0.008,
            criteria_pass=5,
            criteria_total=5,
        ),
    ]
    conn = _setup_db(tmp_path, runs)
    result = analyze("t1", conn)
    assert "vanilla" in result
    assert "package-b" in result
    assert "(baseline)" in result
    conn.close()


def test_analyze_mixed_agents_uses_per_agent_baseline(tmp_path):
    """Each agent's packages should be compared against that agent's vanilla baseline."""
    runs = [
        Run(
            task_id="t1", agent="claude", package_name="vanilla",
            input_tokens=100, output_tokens=50, total_cost_usd=0.10,
            criteria_pass=2, criteria_total=2,
        ),
        Run(
            task_id="t1", agent="claude", package_name="pkg-a",
            input_tokens=80, output_tokens=40, total_cost_usd=0.08,
            criteria_pass=2, criteria_total=2,
        ),
        Run(
            task_id="t1", agent="codex", package_name="vanilla",
            input_tokens=200, output_tokens=100, total_cost_usd=0.20,
            criteria_pass=2, criteria_total=2,
        ),
        Run(
            task_id="t1", agent="codex", package_name="pkg-a",
            input_tokens=300, output_tokens=150, total_cost_usd=0.30,
            criteria_pass=2, criteria_total=2,
        ),
    ]
    conn = _setup_db(tmp_path, runs)
    result = analyze("t1", conn)
    # claude:pkg-a is -20% vs claude:vanilla (0.08 vs 0.10)
    assert "-20.0%" in result
    # codex:pkg-a is +50% vs codex:vanilla (0.30 vs 0.20)
    assert "+50.0%" in result
    # Both vanillas should be baselines
    lines = result.split("\n")
    baseline_lines = [line for line in lines if "(baseline)" in line]
    assert len(baseline_lines) == 2
    conn.close()


def test_analyze_with_quality_scores(tmp_path):
    scores = json.dumps([{"dimension": "correctness", "score": 0.9, "reason": "good"}])
    runs = [
        Run(task_id="t1", package_name="vanilla", total_cost_usd=0.01, quality_scores=scores),
    ]
    conn = _setup_db(tmp_path, runs)
    result = analyze("t1", conn)
    assert "vanilla" in result
    conn.close()
