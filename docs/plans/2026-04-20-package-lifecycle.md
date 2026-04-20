# Package Lifecycle Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend token_miser's environment setup to benchmark hook-based, plugin-based, and (future) MCP-based packages — not just CLAUDE.md configs.

**Architecture:** The manifest.yaml gains an optional `settings` key pointing to a settings.json file. During environment setup, if a package contains settings.json, it gets deep-merged into the temp home's `.claude/settings.json`. A new `services` key lists processes to start before benchmarking and kill during teardown. This aligns with kanon's model (everything is a package, lifecycle differs by type) without duplicating kanon's distribution or registration concerns.

**Tech Stack:** Python, PyYAML, pytest, existing token_miser modules (environment.py, package_adapter.py)

**Key context for the implementer:**
- `environment.py:setup_env()` creates `/tmp/experiment-XXXX/` as HOME, clones task repo to `workspace/`, copies `.claude/` config
- `package_adapter.py:apply_package()` reads `manifest.yaml`, copies `targets` list files into `.claude/` dir
- rtk package already ships `settings.json` + `hooks/` + `bin/rtk` as targets — but `_setup_claude_home()` never merges settings.json
- The rtk hook gracefully degrades (warns on stderr, exits 0) if the binary is missing — so hook packages work without binaries for "does the hook overhead cost tokens" tests
- Claude Code settings.json lives at `~/.claude/settings.json` (NOT inside `.claude/` subdir)
- Kanon MCP support is planned but not shipped — design for it but don't implement the MCP lifecycle yet

---

### Task 1: Settings.json Deep-Merge in Environment Setup

The core fix: when a package ships a `settings.json`, merge it into the experiment's `.claude/settings.json`. This unblocks rtk and any future hook-based package.

**Files:**
- Modify: `src/token_miser/environment.py:33-53` (`_setup_claude_home`)
- Test: `tests/test_environment.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_environment.py`:

```python
"""Tests for environment setup — settings.json merge and service lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from token_miser.environment import _setup_claude_home
from token_miser.package_ref import PackageRef


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    (claude_dir / ".credentials.json").write_text('{"token": "fake"}')
    return home


@pytest.fixture
def hook_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "hook-pkg"
    pkg.mkdir()
    (pkg / "manifest.yaml").write_text(yaml.dump({
        "name": "hook-pkg",
        "version": "0.1.0",
        "author": "test",
        "description": "test hook package",
        "targets": [
            {"path": "hooks/my-hook.sh", "dest": "hooks/my-hook.sh"},
            {"path": "settings.json", "dest": "settings.json"},
        ],
    }))
    hooks_dir = pkg / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "my-hook.sh").write_text("#!/bin/bash\nexit 0\n")
    (pkg / "settings.json").write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "$HOME/.claude/hooks/my-hook.sh"}],
            }],
        },
    }))
    return pkg


class TestSetupClaudeHomeWithHooks:
    def test_merges_package_settings_into_claude_dir(
        self, tmp_path: Path, fake_home: Path, hook_package: Path,
    ) -> None:
        experiment_home = tmp_path / "experiment"
        experiment_home.mkdir()
        ref = PackageRef(name="hook-pkg", package_path=str(hook_package))

        _setup_claude_home(str(experiment_home), ref, fake_home)

        settings_path = experiment_home / ".claude" / "settings.json"
        assert settings_path.exists(), "settings.json should be placed in .claude/"
        settings = json.loads(settings_path.read_text())
        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]

    def test_merges_with_existing_settings(
        self, tmp_path: Path, fake_home: Path, hook_package: Path,
    ) -> None:
        experiment_home = tmp_path / "experiment"
        experiment_home.mkdir()
        claude_dir = experiment_home / ".claude"
        claude_dir.mkdir(mode=0o700)
        (claude_dir / "settings.json").write_text(json.dumps({
            "permissions": {"allow": ["Read"]},
        }))
        ref = PackageRef(name="hook-pkg", package_path=str(hook_package))

        _setup_claude_home(str(experiment_home), ref, fake_home)

        settings = json.loads((claude_dir / "settings.json").read_text())
        assert settings["permissions"]["allow"] == ["Read"]
        assert "PreToolUse" in settings["hooks"]

    def test_no_settings_json_leaves_claude_dir_unchanged(
        self, tmp_path: Path, fake_home: Path,
    ) -> None:
        simple_pkg = tmp_path / "simple-pkg"
        simple_pkg.mkdir()
        (simple_pkg / "manifest.yaml").write_text(yaml.dump({
            "name": "simple",
            "version": "0.1.0",
            "author": "test",
            "description": "no hooks",
            "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
        }))
        (simple_pkg / "CLAUDE.md").write_text("# test\n")

        experiment_home = tmp_path / "experiment"
        experiment_home.mkdir()
        ref = PackageRef(name="simple", package_path=str(simple_pkg))

        _setup_claude_home(str(experiment_home), ref, fake_home)

        assert not (experiment_home / ".claude" / "settings.json").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_environment.py -v`
Expected: FAIL — `test_merges_package_settings_into_claude_dir` fails because `_setup_claude_home` doesn't merge settings.json

**Step 3: Implement settings.json merge**

In `src/token_miser/environment.py`, add a `_merge_settings` helper and call it from `_setup_claude_home`:

```python
def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base. Lists are concatenated."""
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        elif key in result and isinstance(result[key], list) and isinstance(val, list):
            result[key] = result[key] + val
        else:
            result[key] = val
    return result


def _merge_package_settings(claude_dir: Path, package_dir: Path) -> None:
    """If the package ships a settings.json, deep-merge it into the experiment's settings."""
    pkg_settings = package_dir / "settings.json"
    if not pkg_settings.exists():
        return

    import json

    overlay = json.loads(pkg_settings.read_text())
    existing_path = claude_dir / "settings.json"
    if existing_path.exists():
        base = json.loads(existing_path.read_text())
    else:
        base = {}

    merged = _deep_merge(base, overlay)
    existing_path.write_text(json.dumps(merged, indent=2) + "\n")
```

Then in `_setup_claude_home`, after `apply_package` and before the AGENTS.md logic, add:

```python
    if package_ref.package_path:
        apply_package(Path(package_ref.package_path), claude_dir)
        _merge_package_settings(claude_dir, Path(package_ref.package_path))
        # ... existing AGENTS.md logic
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_environment.py -v`
Expected: All 3 tests PASS

**Step 5: Run full test suite for regressions**

Run: `uv run pytest -q`
Expected: All 195+ tests PASS

**Step 6: Commit**

```bash
git add src/token_miser/environment.py tests/test_environment.py
git commit -m "feat: merge package settings.json into experiment environment"
```

---

### Task 2: Service Lifecycle in Manifest

Add optional `services` key to manifest.yaml. During environment setup, start listed processes; during teardown, kill them. This enables claude-mem (worker on port 37777) and future MCP servers.

**Files:**
- Modify: `src/token_miser/environment.py` (EnvironmentContext, setup_env, teardown)
- Modify: `src/token_miser/package_adapter.py:41-89` (validate_package — accept new key)
- Test: `tests/test_environment.py` (add service tests)

**Step 1: Write the failing test**

Append to `tests/test_environment.py`:

```python
import subprocess
import signal
import time


@pytest.fixture
def service_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "svc-pkg"
    pkg.mkdir()
    (pkg / "manifest.yaml").write_text(yaml.dump({
        "name": "svc-pkg",
        "version": "0.1.0",
        "author": "test",
        "description": "package with a service",
        "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
        "services": [{"command": "python3 -m http.server 0", "name": "test-http"}],
    }))
    (pkg / "CLAUDE.md").write_text("# test\n")
    return pkg


class TestServiceLifecycle:
    def test_reads_services_from_manifest(self, service_package: Path) -> None:
        manifest = yaml.safe_load((service_package / "manifest.yaml").read_text())
        assert "services" in manifest
        assert manifest["services"][0]["name"] == "test-http"

    def test_validate_package_accepts_services_key(self, service_package: Path) -> None:
        from token_miser.package_adapter import validate_package
        errors = validate_package(service_package)
        assert errors == []

    def test_environment_context_tracks_pids(self) -> None:
        from token_miser.environment import EnvironmentContext
        ctx = EnvironmentContext(home_dir="/tmp/fake", workspace_dir="/tmp/fake/ws", service_pids=[])
        assert ctx.service_pids == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_environment.py::TestServiceLifecycle -v`
Expected: FAIL — `EnvironmentContext` doesn't have `service_pids`

**Step 3: Add service_pids to EnvironmentContext and update teardown**

In `src/token_miser/environment.py`:

```python
import signal

@dataclass
class EnvironmentContext:
    home_dir: str
    workspace_dir: str
    service_pids: list[int] = None

    def __post_init__(self):
        if self.service_pids is None:
            self.service_pids = []

    def teardown(self) -> None:
        for pid in self.service_pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        if self.home_dir:
            shutil.rmtree(self.home_dir, ignore_errors=True)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_environment.py::TestServiceLifecycle -v`
Expected: All 3 PASS

**Step 5: Commit**

```bash
git add src/token_miser/environment.py tests/test_environment.py
git commit -m "feat: add service_pids tracking to EnvironmentContext"
```

---

### Task 3: Start/Stop Services During Setup

Wire up the service start/stop lifecycle into `setup_env` and `teardown`.

**Files:**
- Modify: `src/token_miser/environment.py` (setup_env — read manifest services, start processes)
- Test: `tests/test_environment.py` (integration test with real subprocess)

**Step 1: Write the failing test**

Append to `tests/test_environment.py`:

```python
class TestServiceStartStop:
    def test_starts_and_stops_service(self, tmp_path: Path) -> None:
        from token_miser.environment import _start_services, EnvironmentContext

        pidfile = tmp_path / "running.pid"
        # A service that writes its PID to a file and sleeps
        cmd = f"python3 -c \"import os, time; open('{pidfile}', 'w').write(str(os.getpid())); time.sleep(60)\""
        services = [{"command": cmd, "name": "test-svc"}]

        ctx = EnvironmentContext(
            home_dir=str(tmp_path / "home"),
            workspace_dir=str(tmp_path / "ws"),
        )
        (tmp_path / "home").mkdir()
        (tmp_path / "ws").mkdir()

        _start_services(services, ctx)

        assert len(ctx.service_pids) == 1
        pid = ctx.service_pids[0]
        # Process should be running
        os.kill(pid, 0)  # raises if not running

        ctx.teardown()

        time.sleep(0.2)
        with pytest.raises(OSError):
            os.kill(pid, 0)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_environment.py::TestServiceStartStop -v`
Expected: FAIL — `_start_services` doesn't exist

**Step 3: Implement _start_services and wire into setup_env**

In `src/token_miser/environment.py`:

```python
def _start_services(services: list[dict], ctx: EnvironmentContext) -> None:
    """Start background services listed in a package manifest."""
    for svc in services:
        cmd = svc.get("command", "")
        name = svc.get("name", cmd[:40])
        if not cmd:
            continue
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=ctx.workspace_dir,
                env={**os.environ, "HOME": ctx.home_dir},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            ctx.service_pids.append(proc.pid)
        except Exception as e:
            print(f"WARNING: failed to start service '{name}': {e}", file=sys.stderr)


def _read_manifest_services(package_path: Path) -> list[dict]:
    """Read services list from a package manifest, if present."""
    manifest = package_path / "manifest.yaml"
    if not manifest.exists():
        return []
    import yaml
    data = yaml.safe_load(manifest.read_text())
    return data.get("services") or []
```

Then in `setup_env`, after the agent-specific setup block and before the return:

```python
        # Start package services (hooks workers, MCP servers, etc.)
        if package_ref.package_path:
            services = _read_manifest_services(Path(package_ref.package_path))
            if services:
                _start_services(services, env)
```

Add `import sys` and `import yaml` at top of file (yaml only needed inside the helper).

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_environment.py::TestServiceStartStop -v`
Expected: PASS

**Step 5: Run full suite**

Run: `uv run pytest -q`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/token_miser/environment.py tests/test_environment.py
git commit -m "feat: start/stop package services during benchmark lifecycle"
```

---

### Task 4: Validate Services Key in Manifest

Update `validate_package` to accept and validate the `services` key so packages with services pass validation cleanly.

**Files:**
- Modify: `src/token_miser/package_adapter.py:41-89` (validate_package)
- Test: `tests/test_package_adapter.py` (add services validation tests)

**Step 1: Write the failing test**

Append to `tests/test_package_adapter.py`:

```python
class TestValidatePackageServices:
    def test_accepts_valid_services(self, tmp_path: Path) -> None:
        pkg = tmp_path / "svc-pkg"
        pkg.mkdir()
        (pkg / "manifest.yaml").write_text(yaml.dump({
            "name": "svc-pkg",
            "version": "0.1.0",
            "author": "test",
            "description": "has services",
            "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
            "services": [{"command": "sleep 60", "name": "sleeper"}],
        }))
        (pkg / "CLAUDE.md").write_text("# test\n")
        errors = validate_package(pkg)
        assert errors == []

    def test_rejects_service_without_command(self, tmp_path: Path) -> None:
        pkg = tmp_path / "bad-svc"
        pkg.mkdir()
        (pkg / "manifest.yaml").write_text(yaml.dump({
            "name": "bad-svc",
            "version": "0.1.0",
            "author": "test",
            "description": "bad service",
            "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
            "services": [{"name": "no-cmd"}],
        }))
        (pkg / "CLAUDE.md").write_text("# test\n")
        errors = validate_package(pkg)
        assert any("command" in e for e in errors)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package_adapter.py::TestValidatePackageServices -v`
Expected: FAIL — `test_rejects_service_without_command` passes vacuously (no validation), but we want explicit validation

**Step 3: Add services validation**

In `src/token_miser/package_adapter.py`, at the end of `validate_package` (before `return errors`):

```python
    services = data.get("services") or []
    for i, svc in enumerate(services):
        if not isinstance(svc, dict):
            errors.append(f"service {i} is not a mapping")
            continue
        if "command" not in svc or not svc["command"]:
            errors.append(f"service {i} missing 'command'")
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_package_adapter.py::TestValidatePackageServices -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/token_miser/package_adapter.py tests/test_package_adapter.py
git commit -m "feat: validate services key in package manifest"
```

---

### Task 5: Create claude-mem Benchmark Package

Create a package wrapper for claude-mem that starts the worker service and installs hooks. This is the first real-world service package.

**Files:**
- Create: `packages/claude-mem/manifest.yaml`
- Create: `packages/claude-mem/CLAUDE.md`
- Create: `packages/claude-mem/settings.json`

**Step 1: Check that the claude-mem worker is buildable**

Run: `ls ~/.claude/plugins/marketplaces/thedotmack/plugin/scripts/`
Verify: `worker-service.cjs` and hook scripts exist

**Step 2: Create the package**

`packages/claude-mem/manifest.yaml`:
```yaml
name: claude-mem
version: 0.1.0
author: thedotmack
description: Claude-mem persistent memory plugin — hooks capture tool usage, worker compresses and stores observations
notes: "Requires claude-mem worker running at localhost:37777. Start with: bun run ~/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs"
targets:
  - path: CLAUDE.md
    dest: CLAUDE.md
  - path: settings.json
    dest: settings.json
services:
  - command: "node $HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs"
    name: claude-mem-worker
```

`packages/claude-mem/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node $HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/claude-mem/session-start-hook.js"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node $HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/claude-mem/post-tool-use-hook.js"
          }
        ]
      }
    ]
  }
}
```

`packages/claude-mem/CLAUDE.md`:
```markdown
# claude-mem active

Memory hooks are installed. Tool usage is being observed and compressed for future session context.
```

**Step 3: Validate the package**

Run: `uv run token-miser list` — verify `claude-mem` appears
Run: `uv run python -c "from token_miser.package_adapter import validate_package; from pathlib import Path; print(validate_package(Path('packages/claude-mem')))"`
Expected: `[]` (no errors)

**Step 4: Commit**

```bash
git add packages/claude-mem/
git commit -m "feat: add claude-mem benchmark package (hook + service lifecycle)"
```

---

### Task 6: Update Dashboard for New Package Types

Add a visual indicator on the dashboard for package types (config, hook, plugin, MCP) so visitors can see what kind of package each is.

**Files:**
- Modify: `docs/index.html` (add type badges to package cards)

**Step 1: Add package type tags**

In the CSS section of `docs/index.html`, add:

```css
.tag-config  { background: rgba(88,166,255,0.15); color: var(--accent); }
.tag-hook    { background: rgba(240,136,62,0.15);  color: var(--orange); }
.tag-plugin  { background: rgba(188,140,255,0.15); color: var(--purple); }
.tag-mcp     { background: rgba(63,185,80,0.15);   color: var(--green); }
```

**Step 2: Add type badges to package cards**

For rtk: `<span class="tag tag-hook">hook</span>` after the package name
For claude-mem: `<span class="tag tag-plugin">plugin</span>` after the package name
For others: `<span class="tag tag-config">config</span>` (or omit — config is the default)

**Step 3: Add rtk and claude-mem cards to the "Available" section**

```html
<div class="pkg-card">
  <h4><a href="https://github.com/rubin-johnson/rtk">rtk</a> <span class="tag tag-hook">hook</span></h4>
  <p>Rust CLI proxy that compresses verbose command outputs via a PreToolUse hook, reducing token consumption on bash-heavy tasks.</p>
  <div class="dim">Token compression</div>
</div>
<div class="pkg-card">
  <h4>claude-mem <span class="tag tag-plugin">plugin</span></h4>
  <p>Persistent memory across sessions — hooks capture tool usage, worker compresses observations, injects relevant context into future sessions.</p>
  <div class="dim">Memory / Context</div>
</div>
```

**Step 4: Commit**

```bash
git add docs/index.html
git commit -m "feat: add hook/plugin type badges to dashboard package cards"
```

---

## What This Does NOT Build (Kanon's Job)

- Package distribution/versioning (kanon owns this)
- MCP server registration (`claude mcp add` — kanon's `KANON_MCP_INSTALL=true`)
- Plugin marketplace registration (`claude plugin install` — kanon's `KANON_MARKETPLACE_INSTALL=true`)
- Token consumption telemetry (kanon "coming soon")

Token_miser's unique value: **run the task, measure the outcome, compare packages**. Kanon distributes; token_miser benchmarks.

## Future (When Kanon Ships MCP)

When `KANON_MCP_INSTALL=true` is available, an MCP package would look like:

```yaml
name: some-mcp-server
version: 0.1.0
targets:
  - path: mcp-config.json
    dest: mcp-config.json
services:
  - command: "node server.js"
    name: some-mcp
```

The `services` infrastructure built in Tasks 2-3 handles this without changes. The only new thing would be merging `mcp.json` config, which follows the same pattern as settings.json merge (Task 1).
