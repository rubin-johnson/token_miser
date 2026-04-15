"""Isolated experiment environment setup."""
from __future__ import annotations

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


def setup_env(task: Task, package_ref: PackageRef) -> EnvironmentContext:
    """Create an isolated experiment environment.

    1. Create a temp directory as HOME
    2. Clone the task repo into HOME/workspace
    3. Checkout the starting commit
    4. Copy Claude credentials into the isolated HOME
    5. If treatment package, apply loadout package
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
                cmd, shell=True, check=True, capture_output=True, cwd=workspace_dir,
            )

        # Copy credentials into isolated HOME so Claude can authenticate
        real_home = Path.home()
        cred_src = real_home / ".claude" / ".credentials.json"
        if cred_src.exists():
            claude_dir = Path(home_dir) / ".claude"
            claude_dir.mkdir(mode=0o700, exist_ok=True)
            shutil.copy2(cred_src, claude_dir / ".credentials.json")

        # Symlink AWS config so Bedrock/SSO credentials work in the isolated HOME
        aws_dir = real_home / ".aws"
        if aws_dir.is_dir():
            os.symlink(str(aws_dir), os.path.join(home_dir, ".aws"))

        # For treatment package, apply loadout
        if package_ref.package_path:
            claude_dir = Path(home_dir) / ".claude"
            apply_package(Path(package_ref.package_path), claude_dir)

    except Exception:
        env.teardown()
        raise

    return env
