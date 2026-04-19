"""Shared backend interfaces and result models."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT = 600  # 10 minutes


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ExecutorResult:
    result: str = ""
    total_cost_usd: float = 0.0
    usage: Usage = field(default_factory=Usage)
    wall_seconds: float = 0.0


class BaseBackend(ABC):
    """Agent backend contract."""

    name: str
    default_model: str | None = None
    instruction_filename: str | None = None

    def resolve_model(self, model: str | None) -> str:
        return model or self.default_model or ""

    def env_file_path(self) -> Path:
        return Path.home() / ".token_miser" / f"{self.name}.env"

    def load_env(self, path: Path | None = None) -> dict[str, str]:
        """Load KEY=VALUE pairs from a backend-specific env file."""
        p = path or self.env_file_path()
        if not p.exists():
            return {}

        extra: dict[str, str] = {}
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            extra[key.strip()] = val.strip()
        return extra

    def estimate_cost(self, usage: Usage, model: str = "") -> float:
        """Estimate cost in USD for the given usage. Returns 0.0 if pricing is unknown."""
        return 0.0

    @abstractmethod
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
        """Execute a single prompt against a workspace."""

    def run_sequential(
        self,
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
            res = self.run(
                prompt,
                home_dir,
                workspace_dir,
                timeout=timeout,
                extra_env=extra_env,
                bare=bare,
                model=model,
            )
            total.total_cost_usd += res.total_cost_usd
            total.usage.input_tokens += res.usage.input_tokens
            total.usage.output_tokens += res.usage.output_tokens
            total.usage.cache_creation_input_tokens += res.usage.cache_creation_input_tokens
            total.usage.cache_read_input_tokens += res.usage.cache_read_input_tokens
            total.usage.reasoning_tokens += res.usage.reasoning_tokens
            total.result = res.result

        total.wall_seconds = time.monotonic() - start
        return total
