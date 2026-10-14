#!/usr/bin/env bash
# Builds the pinned execution environments of the clean reproduction.
#
# Pinned from evidence in the original artifacts:
#   Python 3.10.12, pytest 7.4.0, pluggy 1.3.0  <- "platform darwin -- Python 3.10.12, pytest-7.4.0,
#   pluggy-1.3.0" in 100_300 LOC p2/ChatGPT coverage/sample*/compilation_report.txt
# Assumed (not recorded by the authors):
#   coverage 7.3.2  <- newest coverage.py release between pluggy 1.3.0 (2023-08) and the first
#   repository commit (2024-01-26) that was current for most of that window (2023-10-02 .. 2023-12-14).
#   mccabe 0.7.0    <- "python -m mccabe --min 0" in 0_100 LOC/cyclo_cov.py; version not recorded.
#
# Environments (all under $CR_HOME, outside git):
#   exec      : test execution for the small set (stdlib-only programs)
#   p2        : test execution for the 100-300 LOC p2 set (project dependencies, env/requirements_p2.txt)
#   p1        : test execution for the 100-300 LOC p1 set (RQ2 inputs, env/requirements_p1.txt)
#   analysis  : statistics and report (scipy, pandas); never used to run generated tests
set -euo pipefail

CR_HOME="${CR_HOME:-/opt/clean_repro}"
HERE="$(cd "$(dirname "$0")" && pwd)"
INSTALLER="Miniconda3-py310_26.7.1-1-Linux-x86_64.sh"
CONDA="$CR_HOME/conda/bin/conda"

mkdir -p "$CR_HOME"
if [ ! -x "$CONDA" ]; then
  curl -sSL -o "$CR_HOME/$INSTALLER" "https://repo.anaconda.com/miniconda/$INSTALLER"
  sha256sum "$CR_HOME/$INSTALLER" > "$HERE/miniconda.sha256"
  bash "$CR_HOME/$INSTALLER" -b -p "$CR_HOME/conda"
fi

make_env() {   # make_env <name> <requirements file>
  local name="$1" req="$2" py="$CR_HOME/conda/envs/$1/bin/python"
  if [ ! -x "$py" ]; then
    CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes "$CONDA" create -y -q -n "$name" --override-channels -c defaults python=3.10.12
  fi
  "$py" -m pip install -q --disable-pip-version-check -r "$req"
  "$py" -m pip freeze --all > "$HERE/lock_${name}.txt"
  "$py" --version >> "$HERE/lock_${name}.txt"
}

make_env exec "$HERE/requirements_exec.txt"
make_env analysis "$HERE/requirements_analysis.txt"
if [ -f "$HERE/requirements_p2.txt" ]; then make_env p2 "$HERE/requirements_p2.txt"; fi
if [ -f "$HERE/requirements_p1.txt" ]; then make_env p1 "$HERE/requirements_p1.txt"; fi
echo "environments ready under $CR_HOME/conda/envs"
