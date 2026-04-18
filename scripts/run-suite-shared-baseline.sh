#!/usr/bin/env bash
set -euo pipefail

BASELINE_MODE=shared "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run-suite-package-matrix.sh"
