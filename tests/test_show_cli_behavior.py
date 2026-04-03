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
