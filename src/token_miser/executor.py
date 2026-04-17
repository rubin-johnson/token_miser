"""Claude CLI invocation with timeout."""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT = 600  # 10 minutes


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class ExecutorResult:
    result: str = ""
    total_cost_usd: float = 0.0
    usage: Usage = field(default_factory=Usage)
    wall_seconds: float = 0.0


def parse_claude_json(data: str | bytes) -> ExecutorResult:
    """Parse Claude CLI JSON output into ExecutorResult."""
    raw = json.loads(data)
    usage_raw = raw.get("usage", {})
    return ExecutorResult(
        result=raw.get("result", ""),
        total_cost_usd=raw.get("total_cost_usd", 0.0),
        usage=Usage(
            input_tokens=usage_raw.get("input_tokens", 0),
            output_tokens=usage_raw.get("output_tokens", 0),
            cache_creation_input_tokens=usage_raw.get("cache_creation_input_tokens", 0),
            cache_read_input_tokens=usage_raw.get("cache_read_input_tokens", 0),
        ),
    )


def _claude_env_path() -> Path:
    return Path.home() / ".token_miser" / "claude.env"


def load_claude_env(path: Path | None = None) -> dict[str, str]:
    """Load KEY=VALUE pairs from the claude.env file.

    These are injected into spawned claude processes but NOT into the
    parent shell, so you can run token_miser under one provider (e.g.
    Anthropic OAuth) while the benchmark processes use another (e.g. Bedrock).
    """
    p = path or _claude_env_path()
    if not p.exists():
        return {}
    extra: dict[str, str] = {}
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        extra[key.strip()] = val.strip()
    return extra


def filter_env(home_dir: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build a clean environment for the subprocess.

    Forwards auth tokens, strips session state, overrides HOME.
    Merges in extra env vars (from claude.env) which override parent env.
    """
    env = {}
    for key, val in os.environ.items():
        if key == "CLAUDECODE":
            continue
        env[key] = val
    if extra:
        env.update(extra)
    env["HOME"] = home_dir
    return env


def run_claude(
    prompt: str,
    home_dir: str,
    workspace_dir: str,
    timeout: int = DEFAULT_TIMEOUT,
    extra_env: dict[str, str] | None = None,
    bare: bool = False,
    model: str | None = None,
) -> ExecutorResult:
    """Execute Claude CLI in an isolated environment."""
    start = time.monotonic()
    env = filter_env(home_dir, extra=extra_env)

    claude_dir = os.path.join(home_dir, ".claude")
    cmd = [
        "claude", "--print", "--dangerously-skip-permissions",
        "--output-format", "json", "--no-session-persistence",
    ]
    if model:
        cmd.extend(["--model", model])
    if bare:
        cmd.append("--bare")
        if os.path.isdir(claude_dir):
            cmd.extend(["--add-dir", claude_dir])

    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        cwd=workspace_dir,
        timeout=timeout,
    )

    if proc.returncode != 0:
        stderr = proc.stderr.strip() if proc.stderr else ""
        stdout_hint = proc.stdout.strip()[:500] if proc.stdout else ""
        details = stderr or stdout_hint or "(no output)"
        raise RuntimeError(f"claude exited {proc.returncode}: {details}")

    result = parse_claude_json(proc.stdout)
    result.wall_seconds = time.monotonic() - start
    return result


def run_claude_sequential(
    prompts: list[str],
    home_dir: str,
    workspace_dir: str,
    timeout: int = DEFAULT_TIMEOUT,
    extra_env: dict[str, str] | None = None,
    bare: bool = False,
    model: str | None = None,
) -> ExecutorResult:
    """Run multiple prompts sequentially, accumulating tokens and cost."""
    total = ExecutorResult()
    start = time.monotonic()

    for prompt in prompts:
        res = run_claude(prompt, home_dir, workspace_dir, timeout=timeout, extra_env=extra_env, bare=bare, model=model)
        total.total_cost_usd += res.total_cost_usd
        total.usage.input_tokens += res.usage.input_tokens
        total.usage.output_tokens += res.usage.output_tokens
        total.usage.cache_creation_input_tokens += res.usage.cache_creation_input_tokens
        total.usage.cache_read_input_tokens += res.usage.cache_read_input_tokens
        total.result = res.result  # keep last step's output

    total.wall_seconds = time.monotonic() - start
    return total
