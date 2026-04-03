import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def build_token_miser(tmpdir: Path) -> Path:
    exe = "token-miser.exe" if sys.platform.startswith("win") else "token-miser"
    bin_path = tmpdir / exe
    cmd = [
        "go",
        "build",
        "-o",
        str(bin_path),
        "./token-miser",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"go build failed:\n{proc.stdout}")
    return bin_path


def test_history_shows_non_zero_wall_time():
    with tempfile.TemporaryDirectory() as d:
        bin_path = build_token_miser(Path(d))
        proc = subprocess.run(
            [str(bin_path), "history"],
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
