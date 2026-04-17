"""Codex CLI backend."""
from __future__ import annotations

import json
import os
import subprocess
import time

from token_miser.backends.base import DEFAULT_TIMEOUT, BaseBackend, ExecutorResult, Usage

_PRICE_PER_MILLION: dict[str, tuple[float, float, float]] = {
    "gpt-5.4": (2.50, 0.25, 15.00),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.2": (1.75, 0.175, 14.00),
    "gpt-5.2-codex": (1.75, 0.175, 14.00),
    "gpt-5.1": (1.25, 0.125, 10.00),
    "gpt-5.1-codex": (1.25, 0.125, 10.00),
    "gpt-5.1-codex-max": (1.25, 0.125, 10.00),
    "gpt-5.1-codex-mini": (1.50, 0.375, 6.00),
    "gpt-5": (1.25, 0.125, 10.00),
    "gpt-5-codex": (1.25, 0.125, 10.00),
    "codex-mini-latest": (1.50, 0.375, 6.00),
}


def _normalize_model(model: str) -> str:
    return model.strip().lower()


def estimate_codex_cost(model: str, usage: Usage) -> float:
    rates = _PRICE_PER_MILLION.get(_normalize_model(model))
    if rates is None:
        return 0.0

    input_rate, cached_rate, output_rate = rates
    cached = min(usage.cache_read_input_tokens, usage.input_tokens)
    uncached = max(usage.input_tokens - cached, 0)
    total = (
        uncached * input_rate
        + cached * cached_rate
        + usage.output_tokens * output_rate
    ) / 1_000_000
    return round(total, 6)


class CodexBackend(BaseBackend):
    name = "codex"
    default_model = "gpt-5.4"
    instruction_filename = "AGENTS.md"

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
        env = dict(os.environ)
        if extra_env:
            env.update(extra_env)
        env["HOME"] = home_dir

        cmd = [
            "codex",
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--full-auto",
            "-C",
            workspace_dir,
        ]
        resolved_model = self.resolve_model(model)
        if resolved_model:
            cmd.extend(["--model", resolved_model])
        # `bare` has no direct Codex analogue today. Keep the signature aligned with Claude.
        cmd.append("-")

        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            env=env,
            cwd=workspace_dir,
            timeout=timeout,
        )

        usage = Usage()
        messages: list[str] = []
        for raw_line in proc.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            item_type = item.get("type")
            if item_type == "item.completed":
                completed = item.get("item", {})
                if completed.get("type") == "agent_message":
                    text = completed.get("text", "")
                    if text:
                        messages.append(text)
            elif item_type == "turn.completed":
                usage_raw = item.get("usage", {})
                usage = Usage(
                    input_tokens=usage_raw.get("input_tokens", 0),
                    output_tokens=usage_raw.get("output_tokens", 0),
                    cache_read_input_tokens=usage_raw.get("cached_input_tokens", 0),
                    reasoning_tokens=usage_raw.get("reasoning_tokens", 0),
                )

        if proc.returncode != 0:
            stderr = proc.stderr.strip() if proc.stderr else ""
            stdout_hint = "\n".join(messages[-2:]).strip()
            details = stderr or stdout_hint or "(no output)"
            raise RuntimeError(f"codex exited {proc.returncode}: {details}")

        result = ExecutorResult(
            result="\n\n".join(messages).strip(),
            total_cost_usd=estimate_codex_cost(resolved_model, usage),
            usage=usage,
            wall_seconds=time.monotonic() - start,
        )
        return result


def load_codex_env(path=None) -> dict[str, str]:
    return CodexBackend().load_env(path)
