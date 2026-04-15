"""SQLite storage for experiment runs."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Run:
    id: int = 0
    task_id: str = ""
    package_name: str = ""
    loadout_name: str = ""
    model: str = ""
    started_at: str = ""
    wall_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_cost_usd: float = 0.0
    exit_code: int = 0
    criteria_pass: int = 0
    criteria_total: int = 0
    quality_scores: str = ""
    result: str = ""


@dataclass
class TuneSession:
    id: int = 0
    suite_name: str = ""
    suite_version: str = ""
    baseline_package: str = ""
    tuned_package: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "running"
    recommendations_json: str = ""


def db_path() -> str:
    home = Path.home()
    return str(home / ".token_miser" / "results.db")


def init_db(path: str | None = None) -> sqlite3.Connection:
    """Initialize database connection and create tables."""
    if path is None:
        path = db_path()
    if path != ":memory:":
        os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            package_name TEXT NOT NULL,
            loadout_name TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            started_at TEXT DEFAULT '',
            wall_seconds REAL NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_read_tokens INTEGER NOT NULL DEFAULT 0,
            cache_write_tokens INTEGER NOT NULL DEFAULT 0,
            total_cost_usd REAL NOT NULL DEFAULT 0,
            exit_code INTEGER NOT NULL DEFAULT 0,
            criteria_pass INTEGER NOT NULL DEFAULT 0,
            criteria_total INTEGER NOT NULL DEFAULT 0,
            quality_scores TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS criterion_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES runs(id),
            criterion_type TEXT,
            passed INTEGER,
            detail TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tune_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite_name TEXT NOT NULL,
            suite_version TEXT NOT NULL DEFAULT '',
            baseline_package TEXT NOT NULL DEFAULT '',
            tuned_package TEXT DEFAULT '',
            started_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            status TEXT DEFAULT 'running',
            recommendations_json TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tune_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER REFERENCES tune_sessions(id),
            run_id INTEGER REFERENCES runs(id),
            phase TEXT NOT NULL
        )
    """)
    conn.commit()

    # Migrate v1 -> v2 column names
    cols = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
    if "arm" in cols:
        conn.execute("ALTER TABLE runs RENAME COLUMN arm TO package_name")
    cols = {row[1] for row in conn.execute("PRAGMA table_info(tune_sessions)").fetchall()}
    if "baseline_profile" in cols:
        conn.execute("ALTER TABLE tune_sessions RENAME COLUMN baseline_profile TO baseline_package")
        conn.execute("ALTER TABLE tune_sessions RENAME COLUMN tuned_profile TO tuned_package")
    conn.commit()


def store_run(conn: sqlite3.Connection, run: Run) -> int:
    """Insert a run and return its ID."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """INSERT INTO runs (task_id, package_name, loadout_name, model, started_at, wall_seconds,
            input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
            total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores, result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run.task_id, run.package_name, run.loadout_name, run.model, now,
            run.wall_seconds, run.input_tokens, run.output_tokens,
            run.cache_read_tokens, run.cache_write_tokens, run.total_cost_usd,
            run.exit_code, run.criteria_pass, run.criteria_total, run.quality_scores, run.result,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    if row_id is None:
        raise RuntimeError("INSERT did not return a row ID")
    return row_id


def get_runs(conn: sqlite3.Connection, task_id: str = "") -> list[Run]:
    """Retrieve runs, optionally filtered by task ID."""
    if task_id:
        rows = conn.execute(
            "SELECT * FROM runs WHERE task_id = ? ORDER BY started_at DESC", (task_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM runs ORDER BY started_at DESC").fetchall()
    return [_row_to_run(r) for r in rows]


def get_run(conn: sqlite3.Connection, run_id: int) -> Run | None:
    """Retrieve a single run by ID."""
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return _row_to_run(row) if row else None


def _row_to_run(row: sqlite3.Row) -> Run:
    return Run(
        id=row["id"],
        task_id=row["task_id"],
        package_name=row["package_name"],
        loadout_name=row["loadout_name"],
        model=row["model"],
        started_at=row["started_at"],
        wall_seconds=row["wall_seconds"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        cache_read_tokens=row["cache_read_tokens"],
        cache_write_tokens=row["cache_write_tokens"],
        total_cost_usd=row["total_cost_usd"],
        exit_code=row["exit_code"],
        criteria_pass=row["criteria_pass"],
        criteria_total=row["criteria_total"],
        quality_scores=row["quality_scores"],
        result=row["result"],
    )


def create_tune_session(conn: sqlite3.Connection, session: TuneSession) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """INSERT INTO tune_sessions (suite_name, suite_version, baseline_package,
            tuned_package, started_at, status, recommendations_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session.suite_name, session.suite_version, session.baseline_package,
         session.tuned_package, now, session.status, session.recommendations_json),
    )
    conn.commit()
    row_id = cursor.lastrowid
    if row_id is None:
        raise RuntimeError("INSERT did not return a row ID")
    return row_id


def update_tune_session(conn: sqlite3.Connection, session_id: int, **kwargs: str) -> None:
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [session_id]
    conn.execute(f"UPDATE tune_sessions SET {sets} WHERE id = ?", values)
    conn.commit()


def link_tune_run(conn: sqlite3.Connection, session_id: int, run_id: int, phase: str) -> None:
    conn.execute(
        "INSERT INTO tune_runs (session_id, run_id, phase) VALUES (?, ?, ?)",
        (session_id, run_id, phase),
    )
    conn.commit()


def get_tune_session(conn: sqlite3.Connection, session_id: int) -> TuneSession | None:
    row = conn.execute("SELECT * FROM tune_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        return None
    return TuneSession(
        id=row["id"],
        suite_name=row["suite_name"],
        suite_version=row["suite_version"],
        baseline_package=row["baseline_package"],
        tuned_package=row["tuned_package"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        status=row["status"],
        recommendations_json=row["recommendations_json"],
    )


def get_tune_session_runs(conn: sqlite3.Connection, session_id: int, phase: str = "") -> list[Run]:
    if phase:
        rows = conn.execute(
            """SELECT r.* FROM runs r
               JOIN tune_runs tr ON r.id = tr.run_id
               WHERE tr.session_id = ? AND tr.phase = ?
               ORDER BY r.started_at""",
            (session_id, phase),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT r.* FROM runs r
               JOIN tune_runs tr ON r.id = tr.run_id
               WHERE tr.session_id = ?
               ORDER BY r.started_at""",
            (session_id,),
        ).fetchall()
    return [_row_to_run(r) for r in rows]


def get_latest_tune_session(conn: sqlite3.Connection, suite_name: str = "") -> TuneSession | None:
    if suite_name:
        row = conn.execute(
            "SELECT * FROM tune_sessions WHERE suite_name = ? ORDER BY started_at DESC LIMIT 1",
            (suite_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM tune_sessions ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return TuneSession(
        id=row["id"],
        suite_name=row["suite_name"],
        suite_version=row["suite_version"],
        baseline_package=row["baseline_package"],
        tuned_package=row["tuned_package"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        status=row["status"],
        recommendations_json=row["recommendations_json"],
    )
