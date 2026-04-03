import sqlite3
import os
import tempfile
import subprocess
import json


def test_persists_result_wall_and_criteria_on_run_completion():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "runs.db")
        # Migrate
        assert subprocess.run(["token-miser", "migrate", "--db", db_path]).returncode == 0
        # Trigger a deterministic test run. Implementation should support a dry-run or seedable mode:
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        fixture = os.path.join(fixtures_dir, "run_input.json")
        rc = subprocess.run([
            "token-miser", "run",
            "--task", "synth-001", "--arm", "treatment",
            "--db", db_path,
            "--fixture", fixture
        ]).returncode
        assert rc == 0

        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT id, result, wall_seconds FROM runs ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        run_id, result, wall = row
        assert isinstance(result, str) and len(result) > 0
        assert isinstance(wall, (int, float)) and wall > 0

        cur.execute("SELECT run_id, criterion_type, passed, detail FROM criterion_results WHERE run_id = ?", (run_id,))
        rows = cur.fetchall()
        assert len(rows) >= 1
        for r in rows:
            assert r[0] == run_id
            assert isinstance(r[1], str) and r[1]
            assert r[2] in (0, 1)
            assert isinstance(r[3], str)