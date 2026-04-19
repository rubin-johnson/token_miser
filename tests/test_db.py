"""Tests for database module."""

from token_miser.db import Run, db_path, get_run, get_runs, init_db, store_run


def test_db_path_env_override(monkeypatch, tmp_path):
    custom = str(tmp_path / "custom.db")
    monkeypatch.setenv("TOKEN_MISER_DB", custom)
    assert db_path() == custom


def test_init_and_store(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    run = Run(task_id="t1", package_name="vanilla", input_tokens=100, output_tokens=50, total_cost_usd=0.01)
    run_id = store_run(conn, run)
    assert run_id > 0
    conn.close()


def test_get_runs_empty(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    runs = get_runs(conn)
    assert runs == []
    conn.close()


def test_get_runs_filtered(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    store_run(conn, Run(task_id="t1", package_name="a"))
    store_run(conn, Run(task_id="t2", package_name="b"))
    runs = get_runs(conn, "t1")
    assert len(runs) == 1
    assert runs[0].task_id == "t1"
    conn.close()


def test_get_run_by_id(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    run_id = store_run(conn, Run(task_id="t1", package_name="vanilla", total_cost_usd=0.05))
    run = get_run(conn, run_id)
    assert run is not None
    assert run.task_id == "t1"
    assert run.total_cost_usd == 0.05
    conn.close()


def test_get_run_not_found(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    run = get_run(conn, 999)
    assert run is None
    conn.close()


def test_roundtrip_all_fields(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    run = Run(
        task_id="full",
        package_name="package-b",
        loadout_name="my-config",
        model="sonnet",
        wall_seconds=12.5,
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
        cache_write_tokens=100,
        total_cost_usd=0.123,
        criteria_pass=3,
        criteria_total=5,
        quality_scores='{"correctness": 0.9}',
        result="some output",
    )
    run_id = store_run(conn, run)
    got = get_run(conn, run_id)
    assert got.package_name == "package-b"
    assert got.loadout_name == "my-config"
    assert got.wall_seconds == 12.5
    assert got.cache_read_tokens == 200
    assert got.quality_scores == '{"correctness": 0.9}'
    conn.close()
