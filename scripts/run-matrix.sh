#!/usr/bin/env bash
# Run a full experiment matrix: vanilla + all kanon-managed bundles on a task.
#
# Usage:
#   EXPERIMENT_REPO_LOADOUT=$HOME/code/personal/loadout ./scripts/run-matrix.sh tasks/loadout-diff-001.yaml
#   EXPERIMENT_REPO_KANON=$HOME/code/caylent/kanon ./scripts/run-matrix.sh tasks/kanon-status-001.yaml
#
# Requires: .packages/ populated by 'kanon install' (or symlinks for dev)
set -euo pipefail

TASK="${1:?Usage: $0 <task.yaml>}"
TIMEOUT="${2:-300}"

if [ ! -d .packages ]; then
    echo "ERROR: .packages/ not found. Run 'kanon install' or create symlinks." >&2
    exit 1
fi

echo "Task: $TASK"
echo "Timeout: ${TIMEOUT}s per invocation"
echo "Bundles: $(ls .packages/ | tr '\n' ' ')"
echo ""

# Run vanilla vs each bundle
for bundle in .packages/*/; do
    name=$(basename "$bundle")
    echo "=== vanilla vs $name ==="
    token-miser run \
        --task "$TASK" \
        --control vanilla \
        --treatment "$bundle" \
        --timeout "$TIMEOUT" || echo "FAILED: $name"
    echo ""
done

# Print analysis
TASK_ID=$(python3 -c "import yaml; print(yaml.safe_load(open('$TASK'))['id'])")
echo "=== Analysis ==="
token-miser analyze --task "$TASK_ID"
