# Public Release Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make token_miser ready for public GitHub release — no install failures, no private content, no embarrassing artifacts, and a first-impression that converts visitors to users.

**Architecture:** Clean in-place: no branch needed, no structural refactors. Each task is an isolated fix. Order matters for Tasks 1–3 (blocking issues first); Tasks 4–9 can be done in any order.

**Tech Stack:** Python/uv, git, pyproject.toml, pytest, SQLite

---

## Task 1: Fix dependency install — loadout git URL + remove local overrides

The single most critical bug: `uv.lock` and `pyproject.toml` hardwire both deps to paths that only exist on your machine. Anyone who runs `uv sync` or `pip install token-miser` gets a broken install.

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock` (regenerated via `uv lock`)

**Step 1: Remove [tool.uv.sources] block and fix loadout dep**

In `pyproject.toml`, change `loadout==0.1.0` to the git URL form and remove the entire `[tool.uv.sources]` section:

```toml
# In [project] dependencies:
"loadout @ git+https://github.com/rubin-johnson/loadout.git@v0.1.0",
"kanon-cli==1.2.0",
```

Remove this block entirely:
```toml
[tool.uv.sources]
loadout = { path = "../loadout", editable = true }
kanon-cli = { path = "../../caylent/kanon", editable = true }
```

**Step 2: Regenerate lock file**

```bash
uv lock
```

Expected: lock file regenerates, both deps resolve from PyPI/git (not local paths).

**Step 3: Verify sync works**

```bash
uv sync
uv run token-miser --help
```

Expected: `token-miser --help` prints usage with no import errors.

**Step 4: Run tests**

```bash
uv run pytest -q
```

Expected: all tests pass.

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "fix: resolve loadout from git URL, remove local path overrides"
```

---

## Task 2: Remove RTK binary from git

A 7.3 MB unverified ELF binary with no source, no build instructions, and a hook that runs on every bash call is a trust killer and a cross-platform failure (silently broken on macOS/ARM).

**Files:**
- Delete: `packages/rtk/bin/rtk` (git rm)
- Modify: `.gitignore`
- Create: `packages/rtk/README.md`
- Modify: `packages/rtk/manifest.yaml`

**Step 1: Remove binary from git**

```bash
git rm packages/rtk/bin/rtk
```

**Step 2: Add gitignore entry**

Add to `.gitignore`:
```
# Compiled package binaries — build locally, do not commit
packages/*/bin/
```

**Step 3: Add a README explaining how to get the binary**

Create `packages/rtk/README.md`:
```markdown
# rtk package

RTK (Rust Token Killer) compresses verbose command outputs via a Claude Code PreToolUse hook,
reducing token consumption from bash-heavy tasks.

## Usage

This package requires a compiled `rtk` binary placed at `bin/rtk` before installation.
The binary is not committed to the repository.

**Get the binary:**
1. Download a release from [rtk releases](https://github.com/rubin-johnson/rtk/releases)
   (Linux x86-64), or
2. Build from source:
   ```bash
   cargo build --release
   cp target/release/rtk packages/rtk/bin/rtk
   ```

Once the binary is in place, install the package normally:
```bash
token-miser run --package rtk --task tasks/synth-001.yaml --baseline vanilla
```

## What it does

The hook intercepts Bash tool output and uses Claude to compress it before it reaches
the main context. On bash-heavy tasks this typically reduces token consumption 20–40%.
```

**Step 4: Mark binary as required in manifest**

In `packages/rtk/manifest.yaml`, add a note:
```yaml
notes: "Requires bin/rtk binary (not included). See README.md for build/download instructions."
```

**Step 5: Verify the packages dir is clean**

```bash
git status packages/rtk/
```

Expected: only `manifest.yaml`, `hooks/`, `settings.json`, `README.md` tracked — no binary.

**Step 6: Commit**

```bash
git add .gitignore packages/rtk/
git commit -m "fix: remove RTK binary, add build instructions"
```

---

## Task 3: Scrub employer content from full-rubin package

`packages/full-rubin/AGENTS.md` contains internal Caylent paths (MCP server locations, Docker compose paths, community skills dir, dotfiles remote URL). These must go before the repo is public.

**Files:**
- Modify: `packages/full-rubin/AGENTS.md`

**Step 1: Remove the Caylent section**

In `packages/full-rubin/AGENTS.md`, delete the entire `## AWS Tooling (Caylent)` section (approximately lines 201–210):

```
## AWS Tooling (Caylent)

- MCP servers (aws-docs, pricing, terraform, diagrams): run via Docker in `~/code/caylent/cae-claude-bestpractices`
  - Start: `cd ~/code/caylent/cae-claude-bestpractices && docker compose up -d`
  - Project MCP config: copy `.mcp.json` to project root
- Skills: `/scaffold` (AWS project generation), `/review-terraform` (code review with Checkov)
- Community skills: `~/code/caylent/caylent-community-skills` — compliance, architecture, SOW review
- For new AWS/Terraform projects: copy `.mcp.json` from cae-claude-bestpractices
```

**Step 2: Remove personal dotfiles remote**

In the `## Dotfiles & Chezmoi` section, remove the line with the personal dotfiles remote:
```
- Dotfiles repo: `~/.local/share/chezmoi` (remote: `github.com:rubin-johnson/dotfiles.git`, branch: `master`)
```

Replace with the generic guidance only:
```
- When modifying chezmoi-managed files: edit the deployed target (e.g. `~/.zshrc`), then `chezmoi re-add <file>`. Never edit the source then re-add.
```

**Step 3: Remove the Data Locations section**

The `## Data Locations` section contains personal tool configs (mempalace, claude-mem) that are environment-specific. Delete the entire section.

**Step 4: Verify no caylent references remain**

```bash
grep -i "caylent\|rubin-johnson/dotfiles\|mempalace\|claude-mem" packages/full-rubin/AGENTS.md
```

Expected: no output.

**Step 5: Commit**

```bash
git add packages/full-rubin/AGENTS.md
git commit -m "fix: remove employer and personal tool paths from full-rubin package"
```

---

## Task 4: Rename personal packages to descriptive names

`slim-rubin` and `full-rubin` are personal identifiers that tell users nothing about what the package does. Rename them to `lean` and `personal`. `drona23` is attribution to the source author and stays.

**Files:**
- Rename: `packages/slim-rubin/` → `packages/lean/`
- Rename: `packages/full-rubin/` → `packages/personal/`
- Modify: `packages/lean/manifest.yaml`
- Modify: `packages/personal/manifest.yaml`
- Modify: `tests/test_package_ref.py` (uses "slim-rubin" as fixture string)
- Modify: `tests/test_digest.py` (uses "slim-rubin" as fixture string)
- Modify: `README.md` (mentions slim-rubin in example)
- Modify: `MEMORY.md` (package list)

**Step 1: Rename directories**

```bash
git mv packages/slim-rubin packages/lean
git mv packages/full-rubin packages/personal
```

**Step 2: Update manifest names**

In `packages/lean/manifest.yaml`, change `name: slim-rubin` to `name: lean`.
In `packages/personal/manifest.yaml`, change `name: full-rubin` to `name: personal`.

**Step 3: Update tests that use the old name as a string literal**

In `tests/test_package_ref.py`, change fixture directory name and assertions from `slim-rubin` to `lean`.
In `tests/test_digest.py`, change `slim-rubin` fixture value to `lean`.

**Step 4: Update README.md example**

Change the example line:
```bash
# Before:
token-miser tune --package slim-rubin
# After:
token-miser tune --package lean
```

**Step 5: Run tests**

```bash
uv run pytest -q
```

Expected: all tests pass.

**Step 6: Commit**

```bash
git add packages/ tests/ README.md
git commit -m "refactor: rename slim-rubin → lean, full-rubin → personal"
```

---

## Task 5: Delete internal task files and .cursor scaffolding

`tasks/kanon-status-001.yaml` and `tasks/loadout-diff-001.yaml` reference private repos no one else has. `.cursor/rules/` files are development artifacts that were accidentally tracked.

**Files:**
- Delete: `tasks/kanon-status-001.yaml`
- Delete: `tasks/loadout-diff-001.yaml`
- Delete: `.cursor/rules/bt-002-compare-per-criterion.mdc`
- Delete: `.cursor/rules/story-004-per-criterion.mdc`

**Step 1: Remove the files**

```bash
git rm tasks/kanon-status-001.yaml tasks/loadout-diff-001.yaml
git rm -r .cursor/
```

**Step 2: Add .cursor to .gitignore**

Verify `.gitignore` has `.cursor/` (it should already). If not, add it.

**Step 3: Verify tasks/ still has public tasks**

```bash
ls tasks/
```

Expected: `quick-001.yaml`, `synth-001.yaml`, `synth-002.yaml`, `synth-003.yaml` remain.

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove internal task files and cursor scaffolding"
```

---

## Task 6: Clean docs/plans of internal artifacts

`docs/plans/ralphael-plan.md` contains a hardcoded local path and references internal story IDs. `docs/plans/critique-and-roadmap.md` is fine to keep — it's useful public context.

**Files:**
- Delete: `docs/plans/ralphael-plan.md`

**Step 1: Delete the file**

```bash
git rm docs/plans/ralphael-plan.md
```

**Step 2: Check critique-and-roadmap.md for internal refs**

```bash
grep -i "caylent\|rujohnson\|/home/\|story-\|bt-0" docs/plans/critique-and-roadmap.md
```

Expected: no output. Fix any hits found.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove internal planning artifacts"
```

---

## Task 7: Add TOKEN_MISER_DB env var override

The DB is hardwired to `~/.token_miser/results.db`. Add a `TOKEN_MISER_DB` override so CI environments and multi-project use don't collide.

**Files:**
- Modify: `src/token_miser/db.py:48-50`
- Modify: `tests/test_db.py` (add env var test)

**Step 1: Write the failing test**

In `tests/test_db.py`, add:

```python
def test_db_path_env_override(monkeypatch, tmp_path):
    custom = str(tmp_path / "custom.db")
    monkeypatch.setenv("TOKEN_MISER_DB", custom)
    assert db_path() == custom
```

**Step 2: Run it to verify it fails**

```bash
uv run pytest tests/test_db.py::test_db_path_env_override -v
```

Expected: FAIL — `db_path()` returns the default path, not the env var value.

**Step 3: Implement the override**

In `src/token_miser/db.py`, update `db_path()`:

```python
def db_path() -> str:
    override = os.environ.get("TOKEN_MISER_DB")
    if override:
        return override
    home = Path.home()
    return str(home / ".token_miser" / "results.db")
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_db.py -q
```

Expected: all pass.

**Step 5: Run full suite**

```bash
uv run pytest -q
```

Expected: all pass.

**Step 6: Commit**

```bash
git add src/token_miser/db.py tests/test_db.py
git commit -m "feat: add TOKEN_MISER_DB env var override for database path"
```

---

## Task 8: Rewrite CHANGELOG

The CHANGELOG describes 3 loadout bundles (there are 14 packages), uses old terminology ("arms", "loadout bundles"), and misrepresents the current state. Rewrite it to reflect reality.

**Files:**
- Modify: `CHANGELOG.md`

**Step 1: Rewrite CHANGELOG.md**

Replace the contents with:

```markdown
# Changelog

## [Unreleased]

## [0.2.0] - 2026-04-18

### Added
- Codex backend (`backends/codex.py`) — run benchmarks against Codex CLI
- `backends/claude.py` — extracted from executor.py for cleaner architecture
- `--agent` flag: `claude`, `codex`, or `both` in all run/tune commands
- `--order baseline-first|package-first` for crossover experimental design
- `scripts/run-suite-package-matrix.sh` — unified matrix runner across agents and packages
- `token-miser list` — shows available packages from the configured packages directory
- `--packages-dir` flag and `TOKEN_MISER_PACKAGES_DIR` env var for configurable packages location
- `TOKEN_MISER_DB` env var override for database path (useful for CI isolation)
- `backend.estimate_cost(usage, model)` — per-backend cost estimation from token counts
- 7 new packages: `caveman`, `c-structured`, `piersede`, `thinking-cap`, `planner`, `drona23`, `adversarial-frugal`
- 3 domain benchmark suites: `domain-python-api`, `domain-iac`, `domain-frontend` (24 tasks total)
- Axis suite: 8 tasks isolating distinct tool-interaction patterns (explore, multiturn, diff, testrun, etc.)
- `token-miser matrix` command — cross-package comparison grid (text + JSON export)

### Changed
- `loadouts/` directory renamed to `packages/` to align with kanon terminology
- Package names: `slim-rubin` → `lean`, `full-rubin` → `personal`
- Dependencies now resolve from PyPI/git rather than local paths

### Fixed
- `--model` flag now propagates correctly to both executor and run command
- `--skip-baseline` now fetches the previous session correctly
- Baseline temp directory no longer leaks on early-exit paths

## [0.1.0] - 2026-04-15

Initial Python release. Complete rewrite from Go.

### Added
- `token-miser run` — execute tasks under baseline and package configurations
- `token-miser compare` — side-by-side comparison of runs
- `token-miser analyze` — statistical summary (mean, stdev, median per package)
- `token-miser history` — list all recorded runs
- `token-miser show` — inspect a specific run in detail
- `token-miser tasks` — list available task YAML files
- `token-miser migrate` — initialize or migrate the database
- `token-miser tune` — automated package evaluation against benchmark suites
- SQLite persistence for all run data
- Three initial packages: `token-miser`, `thorough`, `tdd-strict`
- Kanon integration for distributing packages
- GitHub Actions CI
- Apache 2.0 license

### Removed
- All Go code
```

**Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: rewrite CHANGELOG to reflect current state"
```

---

## Task 9: README and .kanon cleanup pass

README says `uv tool install loadout` (installs wrong PyPI package), and `.kanon` needs a comment clarifying it's an example configuration.

**Files:**
- Modify: `README.md`
- Modify: `.kanon`

**Step 1: Fix loadout install instruction in README**

Find the Requirements section. Change:
```
- [loadout](https://github.com/rubin-johnson/loadout) installed (`uv tool install loadout`)
```
To:
```
- [loadout](https://github.com/rubin-johnson/loadout) — installed automatically via `uv sync` (git dependency)
```

Note: `loadout` on PyPI is an unrelated package. The correct package is installed via the git URL in `pyproject.toml`.

**Step 2: Add CONTRIBUTING note about the loadout PyPI collision**

Add a development note to README (under a `## Development` heading if one doesn't exist):

```markdown
## Development

```bash
# Clone and install
git clone https://github.com/rubin-johnson/token_miser.git
cd token_miser
uv sync
uv run token-miser --help
```

> **Note for contributors:** The `loadout` package dependency resolves from a git URL
> (not PyPI). `uv sync` handles this automatically. Do not run `pip install loadout`
> directly — the PyPI package with that name is unrelated.
```

**Step 3: Add clarifying comment to .kanon**

At the top of `.kanon`, add:
```bash
# This .kanon file is an example showing how to use kanon to distribute packages.
# It points to the author's public package repository at rubin-johnson/loadout-packages.
# Replace GITBASE and KANON_SOURCE_packages_URL to use your own package repository.
```

**Step 4: Final scan for personal data leaks**

```bash
grep -rn "caylent\|rujohnson\|/home/rubin" \
  src/ tests/ packages/ tasks/ benchmarks/ README.md CHANGELOG.md .kanon \
  --include="*.py" --include="*.md" --include="*.yaml" --include="*.toml" \
  --include="*.json" --include="*.sh" 2>/dev/null | grep -v "packages/rtk"
```

Expected: only `rubin-johnson` in manifest.yaml `author:` fields (attribution — fine), README github links (fine), and `.kanon` (now explained by comment). Any other hits must be fixed before continuing.

**Step 5: Commit**

```bash
git add README.md .kanon
git commit -m "docs: fix loadout install instructions, clarify .kanon example config"
```

---

## Final Verification

```bash
# All tests pass
uv run pytest -q

# Lint clean
uv run ruff check src tests

# No personal data remaining
grep -rn "caylent\|@caylent\|caylent\.com" \
  src/ tests/ packages/ tasks/ benchmarks/ README.md \
  --include="*.py" --include="*.md" --include="*.yaml" 2>/dev/null

# Binary not tracked
git ls-files packages/rtk/bin/

# Install smoke test (clean venv)
uv run --isolated token-miser --help
```

After all tasks pass verification, the repo is ready to make public.
