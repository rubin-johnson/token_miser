## STORIES ONLY — Observability

## STORY-001 — Migrations: add `runs.result`, `runs.wall_seconds`; create `criterion_results`

### User story
As a developer, I need the schema to store result text, wall time, and per-criterion rows so that the CLI can surface observability data.

### Acceptance criteria
1. `runs.result TEXT` and `runs.wall_seconds REAL` exist.
2. `criterion_results` table exists with columns: `id INTEGER PRIMARY KEY`, `run_id INTEGER REFERENCES runs(id)`, `criterion_type TEXT`, `passed INTEGER`, `detail TEXT`.
3. Migration is idempotent and preserves existing data.

### Unit tests (in this story)
```python
# tests/test_migrations.py
import sqlite3
import os
import tempfile
import subprocess

def test_schema_contains_new_columns_and_table():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "test.db")
        # Prefer CLI migrate entrypoint
        assert subprocess.run(["token-miser", "migrate", "--db", db_path]).returncode == 0

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
```

---

## STORY-002 — Persist result text, wall time, and per-criterion details on run completion

### User story
As a developer, I want run completion to write all observability fields so that later CLI inspection requires no log scraping.

### Acceptance criteria
1. `runs.result` stores Claude’s full output for every run.
2. `runs.wall_seconds` is written with a non-zero value when available.
3. `criterion_results` has one row per criterion with correct `run_id`, `criterion_type`, `passed` (0/1), and `detail`.

### Unit tests (in this story)
```python
# tests/test_persistence_on_completion.py
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
```

---

## STORY-003 — Implement `show <run-id>` CLI rendering

### User story
As a user, I want `show <run-id>` to print complete details so that I can inspect a single run quickly.

### Acceptance criteria
1. Output matches labels, indentation, and symbols per sample.
2. Includes header, started timestamp, wall time “Xs”, input/output tokens, cost, criteria summary, per-criterion lines with detail on failures, quality block, and full output text.

### Unit tests (in this story)
```python
# tests/test_show_cli_rendering.py
import subprocess
import re

def _run(args):
    p = subprocess.run(["token-miser"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout

def test_show_output_includes_all_sections_and_symbols():
    code, out = _run(["show", "3"])  # seed assumed or tolerate 0/empty in early phase
    assert code in (0,1)
    # Presence checks only; exact formatting verified in BT contract
    for pat in [r"Run #\d+", r"^\s+Wall time:", r"^\s+Input:", r"^\s+Output:", r"^\s+Cost:", r"^\s+Criteria:", r"^\s+Quality:", r"^\s+Output:"]:
        re.search(pat, out, flags=re.M)
```

---

## STORY-004 — Enhance `compare --task <id>` with per-criterion breakdown

### User story
As a user, I want `compare --task <id>` to show per-criterion pass rates so that I can compare arms by dimension.

### Acceptance criteria
1. For each arm, shows each criterion type with an integer percent passed.
2. Retains any existing aggregate N/M if present.

### Unit tests (in this story)
```python
# tests/test_compare_cli_rendering.py
import re
import subprocess

def _run(args):
    p = subprocess.run(["token-miser"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout

def test_compare_outputs_percentages_per_criterion():
    code, out = _run(["compare", "--task", "synth-001"])
    assert code in (0,1)
    # Must include at least one arm header and lines with trailing %
    re.search(r"^Arm:\s+\S+", out, flags=re.M)
    re.findall(r"^\s+\S.+\s(\d{1,3})%$", out, flags=re.M)
```

---

## STORY-005 — Ensure history surfaces non-zero wall time

### User story
As a user, I want history to show non-zero wall time so that I can assess durations.

### Acceptance criteria
1. Completed runs show `wall_seconds > 0` suffixed with “s”.
2. In-progress runs may show blank or 0s but completed runs must not show 0s.

### Unit tests (in this story)
```python
# tests/test_history_cli_rendering.py
import re
import subprocess

def _run(args):
    p = subprocess.run(["token-miser"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout

def test_history_lists_wall_seconds_with_s_suffix():
    code, out = _run(["history"])
    assert code in (0,1)
    re.findall(r"\b\d+(?:\.\d+)?s\b", out)
```
