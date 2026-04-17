#!/usr/bin/env bash
set -euo pipefail

SUITE="axis"
MODEL="opus"
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
echo "Suite: $SUITE | Model: $MODEL | Packages: ${#PACKAGES[@]}"
echo ""

# Phase 1: First package (runs baseline + tuned)
first="${PACKAGES[0]}"
name=$(basename "$first")
echo "--- [1/${#PACKAGES[@]}] $name (+ baseline) ---"
token-miser tune --suite "$SUITE" --model "$MODEL" --timeout "$TIMEOUT" --yes \
    --package "$first" 2>&1 | tee "/tmp/axis-${name}.log"
echo ""

# Phase 2: Remaining packages (reuse baseline)
for i in $(seq 1 $((${#PACKAGES[@]} - 1))); do
    pkg="${PACKAGES[$i]}"
    name=$(basename "$pkg")
    echo "--- [$((i + 1))/${#PACKAGES[@]}] $name (skip baseline) ---"
    token-miser tune --suite "$SUITE" --model "$MODEL" --timeout "$TIMEOUT" --yes \
        --skip-baseline --package "$pkg" 2>&1 | tee "/tmp/axis-${name}.log"
    echo ""
done

echo "=== Matrix complete ==="
