"""Claude Code backend."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from token_miser.backends.base import DEFAULT_TIMEOUT, BaseBackend, ExecutorResult, Usage

# (input_rate, cache_creation_rate, cached_read_rate, output_rate) per million tokens
_CLAUDE_PRICE_PER_MILLION: dict[str, tuple[float, float, float, float]] = {
    "claude-haiku-4-5": (0.80, 1.00, 0.08, 4.00),
    "claude-sonnet-4-6": (3.00, 3.75, 0.30, 15.00),
    "claude-opus-4-6": (15.00, 18.75, 1.50, 75.00),
}
# Alias prefixes → canonical model key
_CLAUDE_ALIAS: dict[str, str] = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}


def _resolve_claude_model_key(model: str) -> str | None:
    m = model.strip().lower()
    if m in _CLAUDE_PRICE_PER_MILLION:
        return m
    for alias, key in _CLAUDE_ALIAS.items():
        if alias in m:
            return key
    return None


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


def filter_env(home_dir: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build a clean environment for Claude subprocesses."""
    env = {}
    for key, val in os.environ.items():
        if key == "CLAUDECODE":
            continue
        env[key] = val
    if extra:
        env.update(extra)
    env["HOME"] = home_dir
    return env


class ClaudeBackend(BaseBackend):
    name = "claude"
    default_model = "sonnet"
    instruction_filename = "CLAUDE.md"

    def estimate_cost(self, usage: Usage, model: str = "") -> float:
        """Estimate cost from token counts (independent of CLI-reported cost)."""
        key = _resolve_claude_model_key(model or self.default_model or "")
        if key is None:
            return 0.0
        input_rate, cache_create_rate, cached_read_rate, output_rate = _CLAUDE_PRICE_PER_MILLION[key]
        cached = min(usage.cache_read_input_tokens, usage.input_tokens)
        uncached = max(usage.input_tokens - cached, 0)
        total = (
            uncached * input_rate
            + cached * cached_read_rate
            + usage.cache_creation_input_tokens * cache_create_rate
            + usage.output_tokens * output_rate
        ) / 1_000_000
        return round(total, 6)

    def run(
        self,
        prompt: str,
        home_dir: str,
        workspace_dir: str,
        timeout: int = DEFAULT_TIMEOUT,
        extra_env: dict[str, str] | None = None,
        bare: bool = False,
        model: str | None = None,
    ) -> ExecutorResult:
        start = time.monotonic()
        env = filter_env(home_dir, extra=extra_env)

        claude_dir = os.path.join(home_dir, ".claude")
        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--output-format",
            "json",
            "--no-session-persistence",
        ]
        resolved_model = self.resolve_model(model)
        if resolved_model:
            cmd.extend(["--model", resolved_model])
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


def load_claude_env(path: Path | None = None) -> dict[str, str]:
    return ClaudeBackend().load_env(path)


def run_claude(
    prompt: str,
    home_dir: str,
    workspace_dir: str,
    timeout: int = DEFAULT_TIMEOUT,
    extra_env: dict[str, str] | None = None,
    bare: bool = False,
    model: str | None = None,
) -> ExecutorResult:
    return ClaudeBackend().run(
        prompt,
        home_dir,
        workspace_dir,
        timeout=timeout,
        extra_env=extra_env,
        bare=bare,
        model=model,
    )


def run_claude_sequential(
    prompts: list[str],
    home_dir: str,
    workspace_dir: str,
    timeout: int = DEFAULT_TIMEOUT,
    extra_env: dict[str, str] | None = None,
    bare: bool = False,
    model: str | None = None,
) -> ExecutorResult:
    return ClaudeBackend().run_sequential(
        prompts,
        home_dir,
        workspace_dir,
        timeout=timeout,
        extra_env=extra_env,
        bare=bare,
        model=model,
    )
