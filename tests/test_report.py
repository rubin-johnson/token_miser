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


def test_compare_two_arms(tmp_path):
    runs = [
        Run(task_id="t1", arm="vanilla", input_tokens=100, output_tokens=50, total_cost_usd=0.01),
        Run(task_id="t1", arm="treatment", input_tokens=80, output_tokens=40, total_cost_usd=0.008),
    ]
    conn = _setup_db(tmp_path, runs)
    result = compare("t1", conn)
    assert "vanilla" in result
    assert "treatment" in result
    assert "|" in result  # side-by-side format
    conn.close()


def test_compare_three_arms(tmp_path):
    runs = [
        Run(task_id="t1", arm="a", total_cost_usd=0.01),
        Run(task_id="t1", arm="b", total_cost_usd=0.02),
        Run(task_id="t1", arm="c", total_cost_usd=0.03),
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
        Run(task_id="t1", arm="vanilla", input_tokens=100, output_tokens=50,
            total_cost_usd=0.01, criteria_pass=3, criteria_total=5),
        Run(task_id="t1", arm="vanilla", input_tokens=120, output_tokens=60,
            total_cost_usd=0.012, criteria_pass=4, criteria_total=5),
        Run(task_id="t1", arm="treatment", input_tokens=80, output_tokens=40,
            total_cost_usd=0.008, criteria_pass=5, criteria_total=5),
    ]
    conn = _setup_db(tmp_path, runs)
    result = analyze("t1", conn)
    assert "vanilla" in result
    assert "treatment" in result
    assert "(baseline)" in result
    conn.close()


def test_analyze_with_quality_scores(tmp_path):
    scores = json.dumps([{"dimension": "correctness", "score": 0.9, "reason": "good"}])
    runs = [
        Run(task_id="t1", arm="vanilla", total_cost_usd=0.01, quality_scores=scores),
    ]
    conn = _setup_db(tmp_path, runs)
    result = analyze("t1", conn)
    assert "vanilla" in result
    conn.close()
