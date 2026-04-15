"""Tests for digest — export, list, compare."""
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
from token_miser.digest import compare_digests, export_all, export_session, list_digests


@pytest.fixture
def conn():
    c = init_db(":memory:")
    yield c
    c.close()


@pytest.fixture
def session_with_runs(conn):
    session = TuneSession(
        suite_name="quick",
        suite_version="0.1.0",
        baseline_profile="vanilla",
        tuned_profile="tuned-v1",
        status="completed",
        recommendations_json='[{"title": "Add grep rule", "category": "token_efficiency", "confidence": 0.9}]',
    )
    sid = create_tune_session(conn, session)

    run_b = Run(task_id="bm-feat-001", arm="vanilla", input_tokens=3000, output_tokens=500,
                total_cost_usd=0.002, wall_seconds=5.0, criteria_pass=2, criteria_total=2)
    run_t = Run(task_id="bm-feat-001", arm="tuned-v1", input_tokens=2000, output_tokens=400,
                total_cost_usd=0.0015, wall_seconds=4.0, criteria_pass=2, criteria_total=2)
    rid_b = store_run(conn, run_b)
    rid_t = store_run(conn, run_t)
    link_tune_run(conn, sid, rid_b, "baseline")
    link_tune_run(conn, sid, rid_t, "tuned")

    return sid


class TestExportSession:
    def test_exports_json_file(self, conn, session_with_runs, tmp_path: Path) -> None:
        path = export_session(conn, session_with_runs, tmp_path)
        assert path.exists()
        assert path.suffix == ".json"

    def test_digest_contains_summary(self, conn, session_with_runs, tmp_path: Path) -> None:
        path = export_session(conn, session_with_runs, tmp_path)
        data = json.loads(path.read_text())
        assert data["type"] == "tune_session"
        assert data["suite"] == "quick"
        assert "baseline" in data["summary"]
        assert "tuned" in data["summary"]

    def test_digest_has_per_run_data(self, conn, session_with_runs, tmp_path: Path) -> None:
        path = export_session(conn, session_with_runs, tmp_path)
        data = json.loads(path.read_text())
        assert len(data["baseline_runs"]) == 1
        assert len(data["tuned_runs"]) == 1
        assert data["baseline_runs"][0]["task_id"] == "bm-feat-001"

    def test_digest_has_recommendations(self, conn, session_with_runs, tmp_path: Path) -> None:
        path = export_session(conn, session_with_runs, tmp_path)
        data = json.loads(path.read_text())
        assert "recommendations" in data
        assert data["recommendations"][0]["title"] == "Add grep rule"

    def test_token_reduction_calculated(self, conn, session_with_runs, tmp_path: Path) -> None:
        path = export_session(conn, session_with_runs, tmp_path)
        data = json.loads(path.read_text())
        # baseline: 3500 tokens, tuned: 2400 tokens
        # reduction = (1 - 2400/3500) * 100 = 31.4%
        assert data["summary"]["token_reduction_pct"] == 31.4

    def test_nonexistent_session_raises(self, conn, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            export_session(conn, 999, tmp_path)


class TestExportAll:
    def test_exports_all_sessions(self, conn, session_with_runs, tmp_path: Path) -> None:
        # Add a second session
        s2 = TuneSession(suite_name="standard", suite_version="0.1.0", baseline_profile="v2")
        create_tune_session(conn, s2)

        paths = export_all(conn, tmp_path)
        assert len(paths) == 2


class TestListDigests:
    def test_lists_json_files(self, tmp_path: Path) -> None:
        (tmp_path / "digest1.json").write_text("{}")
        (tmp_path / "digest2.json").write_text("{}")
        (tmp_path / "other.txt").write_text("not a digest")
        result = list_digests(tmp_path)
        assert len(result) == 2

    def test_empty_dir(self, tmp_path: Path) -> None:
        d = tmp_path / "empty"
        d.mkdir()
        assert list_digests(d) == []


class TestCompareDigests:
    def test_compare_two_digests(self, tmp_path: Path) -> None:
        d1 = {
            "suite": "quick",
            "baseline_profile": "vanilla",
            "summary": {
                "baseline": {"total_tokens": 5000, "total_cost": 0.003},
                "tuned": {"total_tokens": 3500, "total_cost": 0.002},
                "token_reduction_pct": 30.0,
            },
        }
        d2 = {
            "suite": "quick",
            "baseline_profile": "slim-rubin",
            "summary": {
                "baseline": {"total_tokens": 4000, "total_cost": 0.0025},
                "tuned": {"total_tokens": 2800, "total_cost": 0.0018},
                "token_reduction_pct": 30.0,
            },
        }
        p1 = tmp_path / "d1.json"
        p2 = tmp_path / "d2.json"
        p1.write_text(json.dumps(d1))
        p2.write_text(json.dumps(d2))

        output = compare_digests(p1, p2)
        assert "quick" in output
        assert "vanilla" in output
        assert "slim-rubin" in output
