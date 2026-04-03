import sqlite3
import os
import tempfile
import subprocess


def test_schema_contains_new_columns_and_table():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "test.db")
        code = subprocess.run(["token-miser", "migrate", "--db", db_path]).returncode
        assert code == 0

        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("PRAGMA table_info(runs)")
        cols = {row[1]: row[2] for row in cur.fetchall()}
        assert "result" in cols and cols["result"].upper().startswith("TEXT")
        assert "wall_seconds" in cols and cols["wall_seconds"].upper().startswith("REAL")

        cur.execute("PRAGMA table_info(criterion_results)")
        cr_cols = {row[1]: row[2] for row in cur.fetchall()}
        for name, type_prefix in [
            ("id", "INTEGER"),
            ("run_id", "INTEGER"),
            ("criterion_type", "TEXT"),
            ("passed", "INTEGER"),
            ("detail", "TEXT"),
        ]:
            assert name in cr_cols and cr_cols[name].upper().startswith(type_prefix)
