# Agent-Agnostic token_miser — Implementation Plan

## Goal
Make token_miser work with multiple AI coding agents (Claude Code, Cursor, Aider, Cline, Windsurf, Copilot) so loadout packages can be benchmarked across agents.

## Architecture: AgentBackend Protocol

```python
class AgentBackend(Protocol):
    name: str
    def run(self, prompt: str, workdir: Path, timeout: int,
            model: str | None = None) -> RunResult: ...
    def supports_config(self, config_type: str) -> bool: ...
    def apply_config(self, workdir: Path, package_dir: Path) -> None: ...
```

`RunResult` captures: stdout, stderr, exit_code, token_usage (input/output/cache), cost, duration, files_changed.

## Phase 1: Extract ClaudeBackend (weeks 1-2)
- Move Claude-specific logic from `executor.py` into `backends/claude.py`
- `ClaudeBackend.run()` wraps the existing `run_claude()` / `run_claude_sequential()`
- `ClaudeBackend.apply_config()` handles CLAUDE.md + settings.json placement
- `executor.py` becomes a thin dispatcher: `get_backend(name) -> AgentBackend`
- **Tests**: existing tests pass through the new indirection unchanged

## Phase 2: Normalize Token/Cost Reporting (week 3)
- Standardize `RunResult.token_usage` across different output formats
- Claude: parse from `--output-format json` or verbose stderr
- Future agents: each backend implements its own parser
- Cost calculation moves from hardcoded to `backend.cost_per_token()` method
- **Key**: matrix reports work regardless of backend

## Phase 3: Config Mapping Layer (weeks 3-4)
- kanon packages are already agent-agnostic (CLAUDE.md is just markdown)
- Map CLAUDE.md instructions → agent-specific config:
  - Cursor: `.cursorrules` file
  - Aider: `.aider.conf.yml` + conventions file
  - Cline: `.clinerules`
  - Copilot: `.github/copilot-instructions.md`
- `apply_config()` per backend handles the translation
- Settings.json (Claude-specific) gets a `config_overrides` abstraction

## Phase 4: Second Backend — Aider (weeks 4-5)
- Aider is the best second target: CLI-based, scriptable, open-source
- `backends/aider.py`: `AiderBackend` implements the protocol
- Parse aider's output for token usage and cost
- Run the same benchmark suites against both Claude and Aider
- **Validation**: axis suite results across both backends

## Phase 5: CI Matrix & Community (weeks 6+)
- `token-miser tune --backend claude,aider --suite axis` runs full cross-agent matrix
- GitHub Actions workflow for automated benchmarking
- Publish comparison results as a static site or JSON feed
- kanon packages gain `agent_compatibility` metadata

## kanon Is Already Agnostic
kanon distributes packages as git repos with manifest.yaml. The manifest format doesn't assume Claude — it just declares files to place. The agent-specific interpretation happens in the backend's `apply_config()`. No kanon changes needed.

## What Changes in token_miser
| File | Change |
|------|--------|
| `src/token_miser/backends/__init__.py` | AgentBackend protocol + registry |
| `src/token_miser/backends/claude.py` | Extracted from executor.py |
| `src/token_miser/backends/aider.py` | Phase 4 |
| `src/token_miser/executor.py` | Thin dispatcher, delegates to backend |
| `src/token_miser/tune.py` | Accept `--backend` param |
| `src/token_miser/__main__.py` | `--backend` CLI arg |
| `src/token_miser/matrix.py` | Add backend column to reports |
| `benchmarks/tasks/*.yaml` | Add optional `agent_requirements` field |

## Risk: Agent Output Parsing
Each agent formats output differently. Token/cost extraction is the hardest part — some agents don't report tokens at all. Mitigation: make token_usage optional in RunResult, degrade gracefully in reports (show "N/A" instead of failing).
