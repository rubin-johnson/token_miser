#!/usr/bin/env bash
set -euo pipefail

BASELINE_MODE=crossover "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run-suite-package-matrix.sh"
