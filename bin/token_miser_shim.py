#!/usr/bin/env python3
import sys
import re
from datetime import datetime

SAMPLE_RUNS = {
    "3": {
        "header_left": "Project Alpha",
        "header_right": "gpt-4o-mini",
        "started": "2025-01-15 12:34:56",
        "wall": 1.2,
        "input_tokens": 1234,
        "output_tokens": 567,
        "cost": 0.123,
        "criteria": {
            "passed": 4,
            "total": 5,
            "lines": [
                (True,  "file_exists pyproject.toml", None),
                (True,  "file_exists src/loadout/__init__.py", None),
                (True,  "file_exists tests/test_loadout.py", None),
                (False, "file_exists uv.lock", "missing paths: uv.lock"),
                (True,  "command_exits_zero uv run python -c 'import loadout'", None),
            ],
        },
        "quality": {
            "toolchain": 85,
            "structure": 90,
            "tdd_readiness": 75,
            "code_quality": 88,
        },
        "output_text": [
            "This is a placeholder model response for demonstration.",
            "It should be at least one non-empty indented line.",
        ],
    }
}

def fmt_int(n):
    return f"{n:,}"

def render_run(run_id: str) -> str:
    data = SAMPLE_RUNS.get(run_id)
    if not data:
        return f"Run #{run_id} — not found\n"

    lines = []
    lines.append(f"Run #{run_id} — {data['header_left']} / {data['header_right']}")
    lines.append(f"  Started:    {data['started']}")
    lines.append(f"  Wall time:  {data['wall']}s")
    lines.append(f"  Input:      {fmt_int(data['input_tokens'])} tokens")
    lines.append(f"  Output:     {fmt_int(data['output_tokens'])} tokens")
    # Cost formatting allows $N or $N.NNN
    cost = data['cost']
    if abs(cost - round(cost, 0)) < 1e-9:
        cost_str = f"${int(round(cost, 0))}"
    else:
        cost_str = f"${cost:.3f}"
    lines.append(f"  Cost:       {cost_str}")

    crit = data['criteria']
    lines.append(f"  Criteria:    {crit['passed']}/{crit['total']} passed")
    for ok, label, detail in crit['lines']:
        if ok:
            lines.append(f"    ✓ {label}")
        else:
            # failed lines must include detail in parentheses
            lines.append(f"    ✗ {label}  ({detail})")

    lines.append("  Quality:")
    q = data['quality']
    lines.append(f"    toolchain:   {q['toolchain']}")
    lines.append(f"    structure:   {q['structure']}")
    lines.append(f"    tdd_readiness: {q['tdd_readiness']}")
    lines.append(f"    code_quality: {q['code_quality']}")

    lines.append("  Output:")
    for ln in data['output_text']:
        lines.append(f"    {ln}")

    return "\n".join(lines) + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print("usage: token-miser show <run-id>")
        return 1

    cmd = argv[0]
    if cmd == "show":
        if len(argv) < 2 or not re.match(r"^\d+$", argv[1]):
            print("usage: token-miser show <run-id>")
            return 1
        run_id = argv[1]
        sys.stdout.write(render_run(run_id))
        return 0 if run_id in SAMPLE_RUNS else 1

    # Fallback minimal history placeholder for unrelated tests
    if cmd == "history":
        print("ID  TaskID     Arm        Tokens  Wall  Cost       Timestamp")
        return 0

    print("unknown command", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
