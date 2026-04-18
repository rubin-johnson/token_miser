"""Backend registry for supported coding agents."""
from __future__ import annotations

from token_miser.backends.base import DEFAULT_TIMEOUT, BaseBackend, ExecutorResult, Usage
from token_miser.backends.claude import ClaudeBackend
from token_miser.backends.codex import CodexBackend

_ALIASES = {
    "claude": "claude",
    "codex": "codex",
    "openai": "codex",
}

_BACKENDS: dict[str, BaseBackend] = {
    "claude": ClaudeBackend(),
    "codex": CodexBackend(),
}


def get_backend(name: str) -> BaseBackend:
    key = _ALIASES.get(name.strip().lower())
    if key is None or key not in _BACKENDS:
        available = ", ".join(sorted(_BACKENDS))
        raise ValueError(f"Unknown agent backend {name!r} (available: {available}; alias: openai -> codex)")
    return _BACKENDS[key]


def parse_agents(spec: str | None) -> list[str]:
    if not spec:
        return ["claude"]

    tokens = [part.strip().lower() for part in spec.split(",") if part.strip()]
    agents: list[str] = []
    for token in tokens:
        if token == "both":
            agents.extend(["claude", "codex"])
            continue
        agents.append(get_backend(token).name)

    seen: set[str] = set()
    deduped: list[str] = []
    for agent in agents:
        if agent not in seen:
            deduped.append(agent)
            seen.add(agent)
    return deduped


__all__ = [
    "BaseBackend",
    "DEFAULT_TIMEOUT",
    "ExecutorResult",
    "Usage",
    "get_backend",
    "parse_agents",
]
