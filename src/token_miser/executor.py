"""Claude CLI invocation with timeout."""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field

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


def parse_claude_json(data: bytes) -> ExecutorResult:
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


def filter_env(home_dir: str) -> dict[str, str]:
    """Build a clean environment for the subprocess.

    Forwards auth tokens, strips session state, overrides HOME.
    """
    env = {}
    for key, val in os.environ.items():
        if key == "CLAUDECODE":
            continue
        env[key] = val
    env["HOME"] = home_dir
    return env


def run_claude(prompt: str, home_dir: str, workspace_dir: str, timeout: int = DEFAULT_TIMEOUT) -> ExecutorResult:
    """Execute Claude CLI in an isolated environment."""
    start = time.monotonic()
    env = filter_env(home_dir)

    proc = subprocess.run(
        ["claude", "--print", "--dangerously-skip-permissions", "--output-format", "json", "--no-session-persistence"],
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        cwd=workspace_dir,
        timeout=timeout,
    )

    if proc.returncode != 0:
        stderr = proc.stderr.strip() if proc.stderr else "(no stderr)"
        raise RuntimeError(f"claude exited {proc.returncode}: {stderr}")

    result = parse_claude_json(proc.stdout.encode())
    result.wall_seconds = time.monotonic() - start
    return result


def run_claude_sequential(
    prompts: list[str], home_dir: str, workspace_dir: str, timeout: int = DEFAULT_TIMEOUT
) -> ExecutorResult:
    """Run multiple prompts sequentially, accumulating tokens and cost."""
    total = ExecutorResult()
    start = time.monotonic()

    for prompt in prompts:
        res = run_claude(prompt, home_dir, workspace_dir, timeout=timeout)
        total.total_cost_usd += res.total_cost_usd
        total.usage.input_tokens += res.usage.input_tokens
        total.usage.output_tokens += res.usage.output_tokens
        total.usage.cache_creation_input_tokens += res.usage.cache_creation_input_tokens
        total.usage.cache_read_input_tokens += res.usage.cache_read_input_tokens
        total.result = res.result  # keep last step's output

    total.wall_seconds = time.monotonic() - start
    return total
