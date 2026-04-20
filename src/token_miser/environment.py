"""Isolated experiment environment setup."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from token_miser.package_adapter import apply_package
from token_miser.package_ref import PackageRef
from token_miser.task import Task


@dataclass
class EnvironmentContext:
    home_dir: str
    workspace_dir: str

    def teardown(self) -> None:
        if self.home_dir:
            shutil.rmtree(self.home_dir, ignore_errors=True)


def _deep_merge(base: dict, overlay: dict) -> dict:
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        elif key in result and isinstance(result[key], list) and isinstance(val, list):
            result[key] = result[key] + val
        else:
            result[key] = val
    return result


def _merge_package_settings(claude_dir: Path, package_dir: Path, pre_existing: dict) -> None:
    pkg_settings = package_dir / "settings.json"
    if not pkg_settings.exists():
        return
    overlay = json.loads(pkg_settings.read_text())
    merged = _deep_merge(pre_existing, overlay)
    (claude_dir / "settings.json").write_text(json.dumps(merged, indent=2) + "\n")


def _copy_if_exists(src: Path, dest: Path) -> None:
    if src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _setup_claude_home(home_dir: str, package_ref: PackageRef, real_home: Path) -> None:
    claude_dir = Path(home_dir) / ".claude"
    claude_dir.mkdir(mode=0o700, exist_ok=True)

    cred_src = real_home / ".claude" / ".credentials.json"
    if cred_src.exists():
        shutil.copy2(cred_src, claude_dir / ".credentials.json")

    claude_md_src = real_home / ".claude" / "CLAUDE.md"
    if claude_md_src.exists():
        shutil.copy2(claude_md_src, claude_dir / "CLAUDE.md")

    if package_ref.package_path:
        existing_settings_path = claude_dir / "settings.json"
        pre_existing = json.loads(existing_settings_path.read_text()) if existing_settings_path.exists() else {}
        apply_package(Path(package_ref.package_path), claude_dir)
        _merge_package_settings(claude_dir, Path(package_ref.package_path), pre_existing)
        package_dir = Path(package_ref.package_path)
        package_agents = package_dir / "AGENTS.md"
        package_claude = package_dir / "CLAUDE.md"
        if package_agents.exists() and not package_claude.exists():
            (claude_dir / "AGENTS.md").write_text(package_agents.read_text())
            (claude_dir / "CLAUDE.md").write_text("@AGENTS.md\n")


def _setup_codex_home(home_dir: str, real_home: Path) -> None:
    codex_dir = Path(home_dir) / ".codex"
    codex_dir.mkdir(mode=0o700, exist_ok=True)
    for name in ("auth.json", "config.toml", "installation_id"):
        _copy_if_exists(real_home / ".codex" / name, codex_dir / name)


def _read_first_existing(paths: list[Path]) -> str:
    for path in paths:
        if path.exists():
            return path.read_text()
    return ""


def _package_instruction_text(package_ref: PackageRef, real_home: Path) -> str:
    if package_ref.package_path:
        package_dir = Path(package_ref.package_path)
        return _read_first_existing([package_dir / "AGENTS.md", package_dir / "CLAUDE.md"])

    return _read_first_existing(
        [
            real_home / ".codex" / "AGENTS.md",
            real_home / ".claude" / "CLAUDE.md",
        ]
    )


def _setup_codex_instructions(workspace_dir: str, package_ref: PackageRef, real_home: Path) -> None:
    package_text = _package_instruction_text(package_ref, real_home).strip()
    if not package_text:
        return

    workspace = Path(workspace_dir)
    existing = _read_first_existing([workspace / "AGENTS.md", workspace / "CLAUDE.md"]).strip()
    sections: list[str] = []
    if existing:
        sections.append(existing)
    sections.append("## token-miser Package Instructions\n\n" + package_text)
    merged = "\n\n".join(section for section in sections if section).rstrip() + "\n"
    (workspace / "AGENTS.md").write_text(merged)


def setup_env(task: Task, package_ref: PackageRef, agent: str = "claude") -> EnvironmentContext:
    """Create an isolated experiment environment.

    1. Create a temp directory as HOME
    2. Clone the task repo into HOME/workspace
    3. Checkout the starting commit
    4. Copy agent credentials into the isolated HOME
    5. If a package is provided, apply agent-specific configuration
    """
    home_dir = tempfile.mkdtemp(prefix="experiment-")
    workspace_dir = os.path.join(home_dir, "workspace")

    env = EnvironmentContext(home_dir=home_dir, workspace_dir=workspace_dir)

    try:
        subprocess.run(
            ["git", "clone", task.repo, workspace_dir],
            check=True,
            capture_output=True,
        )

        # Checkout starting commit
        if task.starting_commit:
            subprocess.run(
                ["git", "-C", workspace_dir, "checkout", task.starting_commit],
                check=True,
                capture_output=True,
            )

        # Run setup commands (e.g., pip install, npm install)
        for cmd in task.setup_commands:
            subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=True,
                cwd=workspace_dir,
            )

        real_home = Path.home()
        # Symlink AWS config so Bedrock/SSO credentials work in the isolated HOME
        aws_dir = real_home / ".aws"
        if aws_dir.is_dir():
            os.symlink(str(aws_dir), os.path.join(home_dir, ".aws"))

        if agent == "claude":
            _setup_claude_home(home_dir, package_ref, real_home)
        elif agent == "codex":
            _setup_codex_home(home_dir, real_home)
            _setup_codex_instructions(workspace_dir, package_ref, real_home)
        else:
            raise ValueError(f"Unsupported agent environment: {agent}")

    except Exception:
        env.teardown()
        raise

    return env
