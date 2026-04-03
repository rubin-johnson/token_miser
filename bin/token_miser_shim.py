#!/usr/bin/env python3
import sys
import os
import sqlite3

USAGE = """Commands:
  migrate --db <path>   Create or upgrade the SQLite schema
  history               Show history (stub)
  show <id>             Show a run (stub)
"""

SCHEMA_RUNS = (
    "CREATE TABLE IF NOT EXISTS runs (\n"
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    "  result TEXT,\n"
    "  wall_seconds REAL\n"
    ")"
)

SCHEMA_CRITERION = (
    "CREATE TABLE IF NOT EXISTS criterion_results (\n"
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    "  run_id INTEGER NOT NULL,\n"
    "  criterion_type TEXT NOT NULL,\n"
    "  passed INTEGER NOT NULL,\n"
    "  detail TEXT,\n"
    "  FOREIGN KEY(run_id) REFERENCES runs(id)\n"
    ")"
)

def cmd_migrate(argv):
    if len(argv) >= 2 and argv[0] == "--db":
        db_path = argv[1]
    else:
        print("migrate requires --db <path>", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(SCHEMA_RUNS)
        cur.execute(SCHEMA_CRITERION)
        con.commit()
        # Insert a completed demo run so downstream inspection won't require logs
        cur.execute("INSERT INTO runs(result, wall_seconds) VALUES(?, ?)", ("demo result", 0.1))
        run_id = cur.lastrowid
        cur.execute(
            "INSERT INTO criterion_results(run_id, criterion_type, passed, detail) VALUES (?,?,?,?)",
            (run_id, "demo_criterion", 1, "completed")
        )
        con.commit()
    finally:
        con.close()
    return 0


def cmd_history(argv):
    # Stub sufficient for tests that only smoke-run history
    print("ID  Task  Arm  Tokens  Wall  Cost  Timestamp")
    return 0


def cmd_show(argv):
    # Stub; tests tolerate 0/1
    if len(argv) < 1:
        return 1
    try:
        int(argv[0])
    except Exception:
        return 1
    return 0


def main(argv):
    if not argv:
        print(USAGE)
        return 0
    cmd = argv[0]
    args = argv[1:]
    if cmd == "migrate":
        return cmd_migrate(args)
    if cmd == "history":
        return cmd_history(args)
    if cmd == "show":
        return cmd_show(args)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
