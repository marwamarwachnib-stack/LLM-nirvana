#!/usr/bin/env bash
# Conda env "p2": the pinned base env (pyng310) plus the 11 benchmark projects of the p2 set.
set -euo pipefail
REPRO_HOME="${REPRO_HOME:-/opt/repro}"
HERE="$(cd "$(dirname "$0")" && pwd)"
CONDA="$REPRO_HOME/conda/bin/conda"
[ -x "$REPRO_HOME/conda/envs/p2/bin/python" ] || "$CONDA" create -y -n p2 --clone pyng310
PY="$REPRO_HOME/conda/envs/p2/bin/python"
"$PY" -m pip install --no-input -r "$HERE/requirements_p2.txt"
"$PY" -m pip freeze > "$HERE/requirements_p2.lock.txt"
