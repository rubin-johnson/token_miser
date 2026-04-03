import re
import sys
import subprocess


def run_cli(args):
    try:
        proc = subprocess.run(
            ["token-miser"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        proc = subprocess.run(
            [sys.executable, "-m", "token_miser"] + args,
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
