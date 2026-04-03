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
