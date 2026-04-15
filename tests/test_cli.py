"""CLI smoke tests."""
import subprocess
import sys


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "token_miser", *args],
        capture_output=True,
        text=True,
    )


def test_help():
    r = _cli("--help")
    assert r.returncode == 0
    assert "Benchmark" in r.stdout


def test_version():
    r = _cli("--version")
    assert r.returncode == 0
    assert "0.1.0" in r.stdout


def test_migrate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    r = _cli("migrate")
    assert r.returncode == 0
    assert "migrations applied" in r.stdout.lower() or "initialized" in r.stdout.lower()


def test_history_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    r = _cli("history")
    assert r.returncode == 0


def test_tasks_lists_yaml(tmp_path):
    (tmp_path / "task.yaml").write_text("id: demo\nname: Demo\nrepo: /tmp/r\nstarting_commit: abc\nprompt: hi\n")
    r = _cli("tasks", "--dir", str(tmp_path))
    assert r.returncode == 0
    assert "demo" in r.stdout
