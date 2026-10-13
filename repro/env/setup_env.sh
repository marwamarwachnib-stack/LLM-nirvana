#!/usr/bin/env bash
# Build the pinned Python environment used by every repro/ script.
#
# Mirrors the original authors' environment as recorded in the repository
# (compilation_report.txt: Python 3.10.12, pytest 7.4.0, pluggy 1.3.0; conda env "pyng310").
# Heavy files (conda, models, ollama) live outside the git repository under $REPRO_HOME.
set -euo pipefail

REPRO_HOME="${REPRO_HOME:-/opt/repro}"
MINICONDA_INSTALLER="Miniconda3-py310_26.7.1-1-Linux-x86_64.sh"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$REPRO_HOME"
if [ ! -x "$REPRO_HOME/conda/bin/conda" ]; then
  curl -sSL -o "$REPRO_HOME/$MINICONDA_INSTALLER" "https://repo.anaconda.com/miniconda/$MINICONDA_INSTALLER"
  bash "$REPRO_HOME/$MINICONDA_INSTALLER" -b -p "$REPRO_HOME/conda"
fi
CONDA="$REPRO_HOME/conda/bin/conda"

# Only the "defaults" channel (repo.anaconda.com) is used.
if [ ! -x "$REPRO_HOME/conda/envs/pyng310/bin/python" ]; then
  CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes "$CONDA" create -y -n pyng310 --override-channels -c defaults python=3.10.12
fi
PY="$REPRO_HOME/conda/envs/pyng310/bin/python"

"$PY" -m pip install --no-input -r "$HERE/requirements.txt"
"$PY" -m pip freeze > "$HERE/requirements.lock.txt"
"$PY" --version
