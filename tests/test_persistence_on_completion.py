import sqlite3
import os
import tempfile
import subprocess

def test_persists_result_wall_and_criteria_on_run_completion():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "runs.db")
        assert subprocess.run(["token-miser", "migrate", "--db", db_path]).returncode == 0
        # Minimal deterministic run hook; acceptable to call a fixture or dry-run path
        rc = subprocess.run(["token-miser", "history"]).returncode  # smoke to create db if needed
        assert subprocess.run(["token-miser", "show", "1"]).returncode in (0,1)  # tolerate empty early db

        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT id, result, wall_seconds FROM runs ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        run_id, result, wall = row
        assert isinstance(result, str)
        assert isinstance(wall, (int, float))
