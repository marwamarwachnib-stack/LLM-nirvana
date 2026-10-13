#!/usr/bin/env bash
# Conda env "p1": the pinned base env plus the libraries needed by the importable p1 modules.
set -euo pipefail
REPRO_HOME="${REPRO_HOME:-/opt/repro}"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -x "$REPRO_HOME/conda/envs/p1/bin/python" ] || "$REPRO_HOME/conda/bin/conda" create -y -n p1 --clone pyng310
"$REPRO_HOME/conda/envs/p1/bin/python" -m pip install --no-input -r "$HERE/requirements_p1.txt"
"$REPRO_HOME/conda/envs/p1/bin/python" -m pip freeze > "$HERE/requirements_p1.lock.txt"
