"""Success criteria verification."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from token_miser.environment import EnvironmentContext
from token_miser.task import Criterion


@dataclass
class CheckResult:
    passed: bool
    detail: str = ""


def check_criterion(criterion: Criterion, env: EnvironmentContext) -> CheckResult:
    """Evaluate a single success criterion."""
    match criterion.type:
        case "file_exists":
            return _check_file_exists(criterion, env)
        case "command_exits_zero" | "command_succeeds":
            return _check_command_exits_zero(criterion, env)
        case "output_contains":
            return _check_output_contains(criterion, env)
        case _:
            return CheckResult(passed=False, detail=f"Unknown criterion type: {criterion.type}")


def check_all_criteria(criteria: list[Criterion], env: EnvironmentContext) -> list[CheckResult]:
    """Evaluate all criteria independently (no short-circuit)."""
    return [check_criterion(c, env) for c in criteria]


def _check_file_exists(criterion: Criterion, env: EnvironmentContext) -> CheckResult:
    missing = [p for p in criterion.paths if not os.path.exists(os.path.join(env.workspace_dir, p))]
    if missing:
        return CheckResult(passed=False, detail=f"Missing files: {', '.join(missing)}")
    return CheckResult(passed=True)


def _check_command_exits_zero(criterion: Criterion, env: EnvironmentContext) -> CheckResult:
    run_env = os.environ.copy()
    run_env["HOME"] = env.home_dir
    try:
        proc = subprocess.run(
            ["sh", "-c", criterion.command],
            cwd=env.workspace_dir,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return CheckResult(passed=True)
        stderr = proc.stderr.strip() if proc.stderr else "(no output)"
        return CheckResult(passed=False, detail=f"Exit code {proc.returncode}: {stderr}")
    except subprocess.TimeoutExpired:
        return CheckResult(passed=False, detail="Command timed out after 120s")


def _check_output_contains(criterion: Criterion, env: EnvironmentContext) -> CheckResult:
    run_env = os.environ.copy()
    run_env["HOME"] = env.home_dir
    try:
        proc = subprocess.run(
            ["sh", "-c", criterion.command],
            cwd=env.workspace_dir,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        missing = [s for s in criterion.contains if s not in proc.stdout]
        if missing:
            return CheckResult(passed=False, detail=f"Missing in output: {', '.join(missing)}")
        if proc.returncode != 0:
            detail = f"Command exited {proc.returncode} (output matched but command failed)"
            return CheckResult(passed=False, detail=detail)
        return CheckResult(passed=True)
    except subprocess.TimeoutExpired:
        return CheckResult(passed=False, detail="Command timed out after 120s")
