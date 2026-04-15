"""Tests for tune — DB schema and session management."""
from __future__ import annotations

import pytest

from token_miser.db import (
    Run,
    TuneSession,
    create_tune_session,
    get_latest_tune_session,
    get_tune_session,
    get_tune_session_runs,
    init_db,
    link_tune_run,
    store_run,
    update_tune_session,
)


@pytest.fixture
def conn():
    c = init_db(":memory:")
    yield c
    c.close()


class TestTuneSessionDB:
    def test_create_session(self, conn) -> None:
        session = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="vanilla")
        sid = create_tune_session(conn, session)
        assert sid > 0

    def test_get_session(self, conn) -> None:
        session = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="vanilla")
        sid = create_tune_session(conn, session)
        result = get_tune_session(conn, sid)
        assert result is not None
        assert result.suite_name == "quick"
        assert result.status == "running"

    def test_update_session(self, conn) -> None:
        session = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="vanilla")
        sid = create_tune_session(conn, session)
        update_tune_session(conn, sid, status="completed", tuned_package="tuned-v1")
        result = get_tune_session(conn, sid)
        assert result is not None
        assert result.status == "completed"
        assert result.tuned_package == "tuned-v1"

    def test_get_nonexistent_session(self, conn) -> None:
        assert get_tune_session(conn, 999) is None


class TestTuneRunLinking:
    def test_link_and_retrieve_runs(self, conn) -> None:
        session = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="vanilla")
        sid = create_tune_session(conn, session)

        run1 = Run(task_id="bm-feat-001", package_name="vanilla", input_tokens=1000, output_tokens=500)
        run2 = Run(task_id="bm-fix-001", package_name="vanilla", input_tokens=2000, output_tokens=800)
        rid1 = store_run(conn, run1)
        rid2 = store_run(conn, run2)

        link_tune_run(conn, sid, rid1, "baseline")
        link_tune_run(conn, sid, rid2, "baseline")

        runs = get_tune_session_runs(conn, sid, "baseline")
        assert len(runs) == 2

    def test_filter_by_phase(self, conn) -> None:
        session = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="vanilla")
        sid = create_tune_session(conn, session)

        run_b = Run(task_id="bm-feat-001", package_name="vanilla", input_tokens=1000, output_tokens=500)
        run_t = Run(task_id="bm-feat-001", package_name="tuned", input_tokens=800, output_tokens=400)
        rid_b = store_run(conn, run_b)
        rid_t = store_run(conn, run_t)

        link_tune_run(conn, sid, rid_b, "baseline")
        link_tune_run(conn, sid, rid_t, "tuned")

        baseline = get_tune_session_runs(conn, sid, "baseline")
        tuned = get_tune_session_runs(conn, sid, "tuned")
        all_runs = get_tune_session_runs(conn, sid)

        assert len(baseline) == 1
        assert len(tuned) == 1
        assert len(all_runs) == 2

    def test_get_all_runs_without_phase(self, conn) -> None:
        session = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="vanilla")
        sid = create_tune_session(conn, session)

        run = Run(task_id="bm-feat-001", package_name="vanilla", input_tokens=1000, output_tokens=500)
        rid = store_run(conn, run)
        link_tune_run(conn, sid, rid, "baseline")

        all_runs = get_tune_session_runs(conn, sid)
        assert len(all_runs) == 1


class TestGetLatestTuneSession:
    def test_returns_latest(self, conn) -> None:
        s1 = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="v1")
        s2 = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="v2")
        create_tune_session(conn, s1)
        create_tune_session(conn, s2)

        latest = get_latest_tune_session(conn, "quick")
        assert latest is not None
        assert latest.baseline_package == "v2"

    def test_filters_by_suite(self, conn) -> None:
        s1 = TuneSession(suite_name="quick", suite_version="0.1.0", baseline_package="v1")
        s2 = TuneSession(suite_name="standard", suite_version="0.1.0", baseline_package="v2")
        create_tune_session(conn, s1)
        create_tune_session(conn, s2)

        latest = get_latest_tune_session(conn, "quick")
        assert latest is not None
        assert latest.suite_name == "quick"

    def test_returns_none_when_empty(self, conn) -> None:
        assert get_latest_tune_session(conn) is None
