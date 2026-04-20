"""Tests for environment setup — settings.json merge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from token_miser.environment import _setup_claude_home
from token_miser.package_ref import PackageRef


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    (claude_dir / ".credentials.json").write_text('{"token": "fake"}')
    return home


@pytest.fixture
def hook_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "hook-pkg"
    pkg.mkdir()
    (pkg / "manifest.yaml").write_text(yaml.dump({
        "name": "hook-pkg",
        "version": "0.1.0",
        "author": "test",
        "description": "test hook package",
        "targets": [
            {"path": "hooks/my-hook.sh", "dest": "hooks/my-hook.sh"},
            {"path": "settings.json", "dest": "settings.json"},
        ],
    }))
    hooks_dir = pkg / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "my-hook.sh").write_text("#!/bin/bash\nexit 0\n")
    (pkg / "settings.json").write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "$HOME/.claude/hooks/my-hook.sh"}],
            }],
        },
    }))
    return pkg


class TestSetupClaudeHomeWithHooks:
    def test_merges_package_settings_into_claude_dir(
        self, tmp_path: Path, fake_home: Path, hook_package: Path,
    ) -> None:
        experiment_home = tmp_path / "experiment"
        experiment_home.mkdir()
        ref = PackageRef(name="hook-pkg", package_path=str(hook_package))

        _setup_claude_home(str(experiment_home), ref, fake_home)

        settings_path = experiment_home / ".claude" / "settings.json"
        assert settings_path.exists(), "settings.json should be placed in .claude/"
        settings = json.loads(settings_path.read_text())
        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]

    def test_merges_with_existing_settings(
        self, tmp_path: Path, fake_home: Path, hook_package: Path,
    ) -> None:
        experiment_home = tmp_path / "experiment"
        experiment_home.mkdir()
        claude_dir = experiment_home / ".claude"
        claude_dir.mkdir(mode=0o700)
        (claude_dir / "settings.json").write_text(json.dumps({
            "permissions": {"allow": ["Read"]},
        }))
        ref = PackageRef(name="hook-pkg", package_path=str(hook_package))

        _setup_claude_home(str(experiment_home), ref, fake_home)

        settings = json.loads((claude_dir / "settings.json").read_text())
        assert settings["permissions"]["allow"] == ["Read"]
        assert "PreToolUse" in settings["hooks"]

    def test_no_settings_json_leaves_claude_dir_unchanged(
        self, tmp_path: Path, fake_home: Path,
    ) -> None:
        simple_pkg = tmp_path / "simple-pkg"
        simple_pkg.mkdir()
        (simple_pkg / "manifest.yaml").write_text(yaml.dump({
            "name": "simple",
            "version": "0.1.0",
            "author": "test",
            "description": "no hooks",
            "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
        }))
        (simple_pkg / "CLAUDE.md").write_text("# test\n")

        experiment_home = tmp_path / "experiment"
        experiment_home.mkdir()
        ref = PackageRef(name="simple", package_path=str(simple_pkg))

        _setup_claude_home(str(experiment_home), ref, fake_home)

        assert not (experiment_home / ".claude" / "settings.json").exists()
