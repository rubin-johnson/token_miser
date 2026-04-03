Dependency graph and execution order:
1) BT-001 → STORY-001 → STORY-003
2) BT-002 → STORY-004
3) BT-003 → STORY-005
4) STORY-002 depends on STORY-001 and unblocks STORY-003/004/005
Recommended execution order: BT-001, BT-002, BT-003, STORY-001, STORY-002, STORY-003, STORY-004, STORY-005

---

## BT-001 — Behavioral test for `show <run-id>` full detail rendering

### User story
As a user, I want `show <run-id>` to print complete run details so that I can inspect results without reading logs.

### Context
Defines the observable CLI behavior and exact formatting for `show`. This is the contract the implementation must satisfy. Copies the sample output verbatim from Original Notes.

### Acceptance criteria
1. Running `token-miser show 3` prints the header, timestamps, wall time, token counts, cost, criteria summary and per-criterion lines, quality block, and full output block.
2. Formatting, labels, and symbols (✓/✗) match the sample structure.

### Unit tests (in this story)
```python
# tests/test_show_cli_behavior.py
import re
import subprocess
import sys

def run_cli(args):
    proc = subprocess.run(
        ["token-miser"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout

def test_show_renders_full_detail_contract():
    # This is a behavioral contract test. It assumes a run id 3 exists in test fixtures.
    # The implementation should provide a seeded DB or a test harness that ensures this data.
    code, out = run_cli(["show", "3"])
    assert code == 0, f"non-zero exit\n{out}"

    # Header and key fields (flexible whitespace, exact labels)
    assert re.search(r"^Run #3 — .+ / .+$", out, flags=re.M), out
    assert re.search(r"^\s+Started:\s+\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", out, flags=re.M), out
    assert re.search(r"^\s+Wall time:\s+\d+(\.\d+)?s$", out, flags=re.M), out
    assert re.search(r"^\s+Input:\s+[\d,]+ tokens$", out, flags=re.M), out
    assert re.search(r"^\s+Output:\s+[\d,]+ tokens$", out, flags=re.M), out
    assert re.search(r"^\s+Cost:\s+\$\d+(\.\d{3})?$", out, flags=re.M), out
    assert re.search(r"^\s+Criteria:\s+\d+/\d+ passed$", out, flags=re.M), out

    # Per-criterion lines must include checkmarks/crosses and type; failed lines include detail in parentheses
    assert re.search(r"^\s+✓\s+\S+", out, flags=re.M), out
    assert re.search(r"^\s+✗\s+\S+.+\(.+\)$", out, flags=re.M), out

    # Quality block with named integer metrics
    assert re.search(r"^\s+Quality:\s*$", out, flags=re.M), out
    for metric in ["toolchain", "structure", "tdd_readiness", "code_quality"]:
        assert re.search(rf"^\s+{metric}:\s+\d+$", out, flags=re.M), f"missing metric {metric}\n{out}"

    # Output block label and at least one non-empty line of Claude's response
    assert re.search(r"^\s+Output:\s*$", out, flags=re.M), out
    assert re.search(r"^\s{4}.+", out, flags=re.M), "Expected at least one line of output text"

def test_show_matches_sample_structure_lines_verbatim_subset():
    # The following subset copied verbatim from Original Notes must appear formatted as shown
    code, out = run_cli(["show", "3"])
    assert code == 0, out
    # Subset of exact lines (allow preceding 2 spaces as in sample)
    required_lines = [
        "  Criteria:    4/5 passed",
        "    ✓ file_exists pyproject.toml",
        "    ✓ file_exists src/loadout/__init__.py",
        "    ✓ file_exists tests/test_loadout.py",
        "    ✗ file_exists uv.lock  (missing paths: uv.lock)",
        "    ✓ command_exits_zero uv run python -c 'import loadout'",
        "  Quality:",
        "    toolchain:   85",
        "    structure:   90",
        "    tdd_readiness: 75",
        "    code_quality: 88",
        "  Output:",
    ]
    for line in required_lines:
        assert line in out, f"Missing line: {line}\n\nActual:\n{out}"
```

### Implementation notes
- Seed test data so that run id 3 produces the exact subset of lines above in the output.
- The CLI command name must be `token-miser` and subcommand `show <run-id>`.
- Use the exact symbols and spacing shown: “✓”, “✗”, two-space indentation before section labels, four spaces before items.

### Dependencies
- None.

---

## BT-002 — Behavioral test for `compare --task <id>` per-criterion pass rates

### User story
As a user, I want `compare --task <id>` to show per-criterion pass rates across arms so that I can compare quality dimensions directly.

### Context
Defines the observable CLI behavior for per-criterion aggregation across arms for a task.

### Acceptance criteria
1. For each arm, output includes each `criterion_type` and a percentage pass rate for that arm/task.
2. Existing aggregate N/M info may remain but cannot replace the per-criterion breakdown.

### Unit tests (in this story)
```python
# tests/test_compare_cli_behavior.py
import re
import subprocess

def run_cli(args):
    proc = subprocess.run(
        ["token-miser"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout

def test_compare_shows_per_criterion_rates_by_arm():
    # Assumes fixtures with task id "synth-001" and at least two arms: control, treatment
    code, out = run_cli(["compare", "--task", "synth-001"])
    assert code == 0, out

    # Must show arm headers and per-criterion % lines. Example:
    # Arm: treatment
    #   file_exists ............ 80%
    #   command_exits_zero ..... 100%
    # Arm: control
    #   file_exists ............ 60%
    #   command_exits_zero ..... 90%
    assert re.search(r"^Arm:\s+\S+", out, flags=re.M), out
    # At least two different criterion types with trailing % per arm
    crit_lines = re.findall(r"^\s+\S[^\n]+?\s(\d{1,3})%$", out, flags=re.M)
    assert len(crit_lines) >= 2, f"Expected per-criterion % lines\n{out}"

def test_compare_keeps_any_aggregate_but_not_instead_of_breakdown():
    code, out = run_cli(["compare", "--task", "synth-001"])
    assert code == 0, out
    # Ensure per-criterion lines are present even if N/M summary is shown
    has_nm = bool(re.search(r"\b\d+/\d+\b", out))
    has_per_criterion = bool(re.search(r"^\s+\S.+\s\d{1,3}%$", out, flags=re.M))
    assert has_per_criterion, f"Per-criterion breakdown missing\n{out}"
```

### Implementation notes
- Group by `arm` and `criterion_type`, compute pass rate = passed_count / total_count for that (task, arm, criterion_type).
- Render per arm with aligned columns and a trailing percent sign.

### Dependencies
- None.

---

## BT-003 — Behavioral test for non-zero wall time in history

### User story
As a user, I want accurate wall-clock time in run history so that I can spot slow runs.

### Context
History/consumption outputs must show `wall_seconds` non-zero after completion.

### Acceptance criteria
1. History view prints a non-zero wall time value (with “s”).
2. Value must be > 0 for completed runs.

### Unit tests (in this story)
```python
# tests/test_history_wall_time.py
import re
import subprocess

def test_history_shows_non_zero_wall_time():
    proc = subprocess.run(
        ["token-miser", "history"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    out = proc.stdout
    assert proc.returncode == 0, out
    # Expect rows like:  2026-03-31 11:09:40   synth-001  treatment  47.3s  $0.046
    times = re.findall(r"\b(\d+(?:\.\d+)?)s\b", out)
    assert any(float(t) > 0.0 for t in times), f"Expected non-zero wall time in history\n{out}"
```

### Implementation notes
- Ensure the history command queries `runs.wall_seconds` and formats with “s”.
- Skip or distinguish in-progress runs where wall time may be 0.

### Dependencies
- None.

---

## STORY-001 — Migrations: add `runs.result`, `runs.wall_seconds`; create `criterion_results`

### User story
As a developer, I need the schema to store result text, wall time, and per-criterion rows so that the CLI can surface observability data.

### Context
Schema changes per PRD: add columns to `runs`; create `criterion_results` table; run-safe migrations without data loss.

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

def test_schema_contains_new_columns_and_table():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "test.db")
        # Implementation should run migrations automatically when connecting/opening
        # or expose a migrate() helper. We call CLI `token-miser migrate` if provided.
        # Fallback: direct function import is allowed if published.
        # Prefer CLI to keep this black-box:
        import subprocess
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
```

### Implementation notes
- Provide a `token-miser migrate --db <path>` command or ensure auto-migrate on open; tests call the CLI.
- Use `ALTER TABLE runs ADD COLUMN` guarded by existence checks; create `criterion_results` only if not exists; add FK to `runs(id)`.

### Dependencies
- BT-001 must be complete.

---

## STORY-002 — Persist result text, wall time, and per-criterion details on run completion

### User story
As a developer, I want run completion to write all observability fields so that later CLI inspection requires no log scraping.

### Context
Populate `runs.result`, `runs.wall_seconds` from `ExecutorResult.WallSeconds`, and insert rows into `criterion_results` per evaluated criterion.

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
import json

def test_persists_result_wall_and_criteria_on_run_completion():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "runs.db")
        # Migrate
        assert subprocess.run(["token-miser", "migrate", "--db", db_path]).returncode == 0
        # Trigger a deterministic test run. Implementation should support a dry-run or seedable mode:
        # token-miser run --task synth-001 --arm treatment --db <db> --fixture tests/fixtures/run_input.json
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
```

### Implementation notes
- When persisting run results, write `runs.result = full_text` and `runs.wall_seconds = ExecutorResult.WallSeconds`.
- Insert per-criterion rows after evaluation; use a single transaction.
- Provide `token-miser run --fixture` or similar deterministic mode for tests.

### Dependencies
- STORY-001 must be complete.

---

## STORY-003 — Implement `show <run-id>` CLI rendering

### User story
As a user, I want `show <run-id>` to print complete details so that I can inspect a single run quickly.

### Context
Renders data persisted by STORY-002 into the exact structure specified.

### Acceptance criteria
1. Output matches labels, indentation, and symbols per sample.
2. Includes header, started timestamp, wall time “Xs”, input/output tokens, cost, criteria summary, per-criterion lines with detail on failures, quality block, and full output text.

### Unit tests (in this story)
```python
# tests/test_show_cli_rendering.py
import subprocess
import re

def test_show_output_includes_all_sections_and_symbols():
    code, out = _run(["show", "3"])
    assert code == 0, out
    required_sections = [
        r"^Run #3 — .+ / .+$",
        r"^\s+Started:",
        r"^\s+Wall time:\s+\d+(\.\d+)?s$",
        r"^\s+Input:\s+[\d,]+ tokens$",
        r"^\s+Output:\s+[\d,]+ tokens$",
        r"^\s+Cost:\s+\$\d+(\.\d{3})?$",
        r"^\s+Criteria:\s+\d+/\d+ passed$",
        r"^\s+Quality:$",
        r"^\s+Output:$",
    ]
    for pat in required_sections:
        assert re.search(pat, out, flags=re.M), f"Missing section {pat}\n{out}"
    assert "✓" in out and "✗" in out, out

def _run(args):
    proc = subprocess.run(["token-miser"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout
```

### Implementation notes
- Query `runs` by id, join any related tables (e.g., qualities), aggregate `criterion_results` to derive X/Y passed, and print each criterion line.
- Use exact Unicode symbols and spacing; indent items by two spaces for section labels, four spaces for list items.

### Dependencies
- BT-001 must be complete.
- STORY-002 must be complete.

---

## STORY-004 — Enhance `compare --task <id>` with per-criterion breakdown

### User story
As a user, I want `compare --task <id>` to show per-criterion pass rates so that I can compare arms by dimension.

### Context
Computes pass rate per `(task, arm, criterion_type)` and renders aligned table per arm.

### Acceptance criteria
1. For each arm, shows each criterion type with an integer percent passed.
2. Retains any existing aggregate N/M if present.

### Unit tests (in this story)
```python
# tests/test_compare_cli_rendering.py
import re
import subprocess

def test_compare_outputs_percentages_per_criterion():
    code, out = _run(["compare", "--task", "synth-001"])
    assert code == 0, out
    # Must include at least one arm header
    assert re.search(r"^Arm:\s+\S+", out, flags=re.M)
    # Must include multiple criterion lines with trailing %
    lines = re.findall(r"^\s+\S.+\s(\d{1,3})%$", out, flags=re.M)
    assert lines and all(0 <= int(p) <= 100 for p in lines)

def _run(args):
    p = subprocess.run(["token-miser"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout
```

### Implementation notes
- SQL: SELECT arm, criterion_type, AVG(passed)*100 FROM criterion_results JOIN runs USING(run_id or runs.id=criterion_results.run_id) WHERE task_id=? GROUP BY arm, criterion_type.
- Render by arm with padded dot leaders and right-aligned percentages.

### Dependencies
- BT-002 must be complete.
- STORY-002 must be complete.

---

## STORY-005 — Ensure history surfaces non-zero wall time

### User story
As a user, I want history to show non-zero wall time so that I can assess durations.

### Context
History view must consume `runs.wall_seconds` and format with “s”.

### Acceptance criteria
1. Completed runs show `wall_seconds > 0` suffixed with “s”.
2. In-progress runs may show blank or 0s but completed runs must not show 0s.

### Unit tests (in this story)
```python
# tests/test_history_cli_rendering.py
import re
import subprocess

def test_history_lists_wall_seconds_with_s_suffix():
    code, out = _run(["history"])
    assert code == 0, out
    times = re.findall(r"\b\d+(?:\.\d+)?s\b", out)
    assert times, f"No wall time values found\n{out}"
    assert any(float(t[:-1]) > 0 for t in times), f"Expected non-zero wall time\n{out}"

def _run(args):
    p = subprocess.run(["token-miser"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout
```

### Implementation notes
- Use `runs.wall_seconds` in history query/formatting; ensure units and non-zero display for completed runs.

### Dependencies
- BT-003 must be complete.
- STORY-002 must be complete.