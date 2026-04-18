#!/usr/bin/env bash
set -euo pipefail

CALLER_CWD="$(pwd)"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SUITE="${SUITE:-quick}"
REPEATS="${REPEATS:-1}"
AGENTS_CSV="${AGENTS:-claude,codex}"
TIMEOUT="${TIMEOUT:-300}"
BASELINE_MODE="${BASELINE_MODE:-shared}"
MODEL="${MODEL:-}"

if [ -n "${PACKAGES_ROOT:-}" ]; then
    case "$PACKAGES_ROOT" in
        /*) ;;
        *) PACKAGES_ROOT="$CALLER_CWD/$PACKAGES_ROOT" ;;
    esac
else
    PACKAGES_ROOT="$REPO_ROOT/packages"
fi

SUITE_FILE="$REPO_ROOT/benchmarks/suites/${SUITE}.yaml"
TASKS_DIR="$REPO_ROOT/benchmarks/tasks"

if [ ! -d "$PACKAGES_ROOT" ]; then
    echo "ERROR: packages root not found: $PACKAGES_ROOT" >&2
    exit 1
fi

if [ ! -f "$SUITE_FILE" ]; then
    echo "ERROR: suite not found: $SUITE_FILE" >&2
    exit 1
fi

mapfile -t PACKAGES < <(find "$PACKAGES_ROOT" -mindepth 1 -maxdepth 1 -type d | sort)
IFS=',' read -r -a AGENTS <<< "$AGENTS_CSV"

if [ "${#PACKAGES[@]}" -eq 0 ]; then
    echo "ERROR: no packages found in $PACKAGES_ROOT" >&2
    exit 1
fi

echo "=== Suite Package Matrix ==="
echo "Suite: $SUITE"
echo "Agents: ${AGENTS[*]}"
echo "Repeats: $REPEATS"
echo "Timeout: ${TIMEOUT}s"
echo "Packages: ${#PACKAGES[@]}"
echo "Baseline mode: $BASELINE_MODE"
echo "Model: ${MODEL:-<default>}"
echo ""

run_shared_mode() {
    local agent="$1"
    local repeat="$2"

    echo "=== Agent: $agent | Repeat: $repeat/$REPEATS | Mode: shared ==="
    for i in "${!PACKAGES[@]}"; do
        pkg="${PACKAGES[$i]}"
        name=$(basename "$pkg")
        echo "--- [$((i + 1))/${#PACKAGES[@]}] $name ---"

        cmd=(
            uv run token-miser tune
            --suite "$SUITE"
            --agent "$agent"
            --timeout "$TIMEOUT"
            --yes
            --package "$pkg"
        )
        if [ -n "$MODEL" ]; then
            cmd+=(--model "$MODEL")
        fi
        if [ "$i" -gt 0 ]; then
            cmd+=(--skip-baseline)
        fi

        log="/tmp/token-miser-${SUITE}-${agent}-shared-r${repeat}-${name}.log"
        "${cmd[@]}" 2>&1 | tee "$log"
        echo ""
    done
}

run_crossover_mode() {
    local agent="$1"
    local repeat="$2"
    local order="baseline-first"
    if [ $((repeat % 2)) -eq 0 ]; then
        order="package-first"
    fi

    mapfile -t TASK_FILES < <(
        uv run python - "$SUITE_FILE" "$TASKS_DIR" <<'PY'
from pathlib import Path
import sys
import yaml

suite_path = Path(sys.argv[1])
tasks_dir = Path(sys.argv[2])
data = yaml.safe_load(suite_path.read_text())
for entry in data.get("tasks", []):
    print(tasks_dir / entry["file"])
PY
    )

    echo "=== Agent: $agent | Repeat: $repeat/$REPEATS | Mode: crossover | Order: $order ==="
    for i in "${!PACKAGES[@]}"; do
        pkg="${PACKAGES[$i]}"
        name=$(basename "$pkg")
        echo "--- [$((i + 1))/${#PACKAGES[@]}] $name ---"

        for task_file in "${TASK_FILES[@]}"; do
            task_name=$(basename "$task_file")
            echo "    -> $task_name"
            cmd=(
                uv run token-miser run
                --agent "$agent"
                --task "$task_file"
                --baseline vanilla
                --package "$pkg"
                --order "$order"
                --timeout "$TIMEOUT"
            )
            if [ -n "$MODEL" ]; then
                cmd+=(--model "$MODEL")
            fi

            log="/tmp/token-miser-${SUITE}-${agent}-crossover-r${repeat}-${name}-${task_name%.yaml}.log"
            "${cmd[@]}" 2>&1 | tee "$log"
        done
        echo ""
    done
}

for agent in "${AGENTS[@]}"; do
    agent="$(echo "$agent" | xargs)"
    [ -n "$agent" ] || continue

    for repeat in $(seq 1 "$REPEATS"); do
        case "$BASELINE_MODE" in
            shared)
                run_shared_mode "$agent" "$repeat"
                ;;
            crossover)
                run_crossover_mode "$agent" "$repeat"
                ;;
            *)
                echo "ERROR: unsupported BASELINE_MODE '$BASELINE_MODE' (use shared or crossover)" >&2
                exit 1
                ;;
        esac
    done
done

echo "=== Matrix complete ==="
