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
    arm: str = ""
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


def db_path() -> str:
    home = Path.home()
    return str(home / ".token_miser" / "results.db")


def init_db(path: str | None = None) -> sqlite3.Connection:
    """Initialize database connection and create tables."""
    if path is None:
        path = db_path()
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
            arm TEXT NOT NULL,
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
    conn.commit()


def store_run(conn: sqlite3.Connection, run: Run) -> int:
    """Insert a run and return its ID."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """INSERT INTO runs (task_id, arm, loadout_name, model, started_at, wall_seconds,
            input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
            total_cost_usd, exit_code, criteria_pass, criteria_total, quality_scores, result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run.task_id, run.arm, run.loadout_name, run.model, now,
            run.wall_seconds, run.input_tokens, run.output_tokens,
            run.cache_read_tokens, run.cache_write_tokens, run.total_cost_usd,
            run.exit_code, run.criteria_pass, run.criteria_total, run.quality_scores, run.result,
        ),
    )
    conn.commit()
    return cursor.lastrowid


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
        arm=row["arm"],
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
