#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SUITE="axis"
AGENT="${AGENT:-claude}"
MODEL="${MODEL:-}"
TIMEOUT=900
PACKAGES=(
    "packages/token-miser"
    "packages/thorough"
    "packages/tdd-strict"
    "packages/slim-rubin"
    "packages/full-rubin"
    "packages/rtk"
)

echo "=== Axis Matrix Benchmark ==="
echo "Suite: $SUITE | Agent: $AGENT | Model: ${MODEL:-<default>} | Packages: ${#PACKAGES[@]}"
echo ""

# Phase 1: First package (runs baseline + tuned)
first="${PACKAGES[0]}"
name=$(basename "$first")
echo "--- [1/${#PACKAGES[@]}] $name (+ baseline) ---"
cmd=(uv run token-miser tune --suite "$SUITE" --agent "$AGENT" --timeout "$TIMEOUT" --yes \
    --package "$first")
if [ -n "$MODEL" ]; then
    cmd+=(--model "$MODEL")
fi
"${cmd[@]}" 2>&1 | tee "/tmp/axis-${AGENT}-${name}.log"
echo ""

# Phase 2: Remaining packages (reuse baseline)
for i in $(seq 1 $((${#PACKAGES[@]} - 1))); do
    pkg="${PACKAGES[$i]}"
    name=$(basename "$pkg")
    echo "--- [$((i + 1))/${#PACKAGES[@]}] $name (skip baseline) ---"
    cmd=(uv run token-miser tune --suite "$SUITE" --agent "$AGENT" --timeout "$TIMEOUT" --yes \
        --skip-baseline --package "$pkg")
    if [ -n "$MODEL" ]; then
        cmd+=(--model "$MODEL")
    fi
    "${cmd[@]}" 2>&1 | tee "/tmp/axis-${AGENT}-${name}.log"
    echo ""
done

echo "=== Matrix complete ==="
