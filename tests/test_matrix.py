"""Tests for matrix — cross-package comparison."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from token_miser.db import (
    Run,
    TuneSession,
    create_tune_session,
    init_db,
    link_tune_run,
    store_run,
)
from token_miser.matrix import build_matrix, export_matrix_json


@pytest.fixture
def conn():
    c = init_db(":memory:")
    yield c
    c.close()


def _seed_session(conn, tuned_package, task_ids, baseline_tokens=1000, tuned_tokens=800):
    session = TuneSession(
        suite_name="axis",
        suite_version="0.1.0",
        baseline_package="vanilla",
        tuned_package=tuned_package,
        status="completed",
    )
    sid = create_tune_session(conn, session)

    for tid in task_ids:
        rb = Run(task_id=tid, package_name="vanilla", input_tokens=baseline_tokens,
                 output_tokens=100, total_cost_usd=0.10, wall_seconds=5.0,
                 criteria_pass=2, criteria_total=2)
        rb_id = store_run(conn, rb)
        link_tune_run(conn, sid, rb_id, "baseline")

        rt = Run(task_id=tid, package_name=tuned_package, input_tokens=tuned_tokens,
                 output_tokens=100, total_cost_usd=0.08, wall_seconds=4.0,
                 criteria_pass=2, criteria_total=2)
        rt_id = store_run(conn, rt)
        link_tune_run(conn, sid, rt_id, "tuned")

    return sid


def test_build_matrix_empty(conn):
    result = build_matrix("nonexistent", conn)
    assert "No tune data" in result


def test_build_matrix_single_package(conn):
    _seed_session(conn, "pkg-a", ["bm-axis-explore", "bm-axis-smallio"])
    result = build_matrix("axis", conn)
    assert "baseline" in result
    assert "pkg-a" in result
    assert "bm-axis-explore" in result
    assert "TOKENS" in result
    assert "COST" in result
    assert "CRITERIA" in result
    assert "DELTA" in result
    assert "TOTALS" in result


def test_build_matrix_multiple_packages(conn):
    _seed_session(conn, "pkg-a", ["bm-axis-explore"], baseline_tokens=1000, tuned_tokens=800)
    _seed_session(conn, "pkg-b", ["bm-axis-explore"], baseline_tokens=1000, tuned_tokens=1200)
    result = build_matrix("axis", conn)
    assert "pkg-a" in result
    assert "pkg-b" in result
    assert "-" in result  # negative delta for pkg-a
    assert "+" in result  # positive delta for pkg-b (or in cost formatting)


def test_build_matrix_pass_fail(conn):
    sid = create_tune_session(conn, TuneSession(
        suite_name="axis", suite_version="0.1.0",
        baseline_package="vanilla", tuned_package="pkg-x", status="completed",
    ))
    rb = Run(task_id="bm-axis-explore", package_name="vanilla", input_tokens=500,
             output_tokens=100, total_cost_usd=0.05, wall_seconds=3.0,
             criteria_pass=1, criteria_total=2)
    rb_id = store_run(conn, rb)
    link_tune_run(conn, sid, rb_id, "baseline")

    rt = Run(task_id="bm-axis-explore", package_name="pkg-x", input_tokens=400,
             output_tokens=100, total_cost_usd=0.04, wall_seconds=2.0,
             criteria_pass=2, criteria_total=2)
    rt_id = store_run(conn, rt)
    link_tune_run(conn, sid, rt_id, "tuned")

    result = build_matrix("axis", conn)
    assert "FAIL 1/2" in result
    assert "PASS 2/2" in result


def test_export_matrix_json(conn, tmp_path):
    _seed_session(conn, "pkg-a", ["bm-axis-explore", "bm-axis-smallio"])
    out = tmp_path / "matrix.json"
    path = export_matrix_json("axis", out, conn)
    assert path.exists()

    data = json.loads(path.read_text())
    assert data["suite"] == "axis"
    assert "baseline" in data["packages"]
    assert "pkg-a" in data["packages"]
    assert "bm-axis-explore" in data["tasks"]
    assert data["matrix"]["bm-axis-explore"]["baseline"]["tokens"] == 1100
    assert data["matrix"]["bm-axis-explore"]["pkg-a"]["tokens"] == 900


def test_export_matrix_json_empty_raises(conn, tmp_path):
    out = tmp_path / "matrix.json"
    with pytest.raises(ValueError, match="No tune data"):
        export_matrix_json("nonexistent", out, conn)
    assert not out.exists()


def test_latest_run_wins(conn):
    _seed_session(conn, "pkg-a", ["bm-axis-explore"], baseline_tokens=1000, tuned_tokens=800)
    _seed_session(conn, "pkg-a", ["bm-axis-explore"], baseline_tokens=2000, tuned_tokens=600)
    result = build_matrix("axis", conn)
    # Latest session's data should win (2000+100=2100 baseline, 600+100=700 tuned)
    assert "2,100" in result
    assert "700" in result
