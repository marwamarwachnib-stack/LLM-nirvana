#!/usr/bin/env bash
# Create the isolated Python 3.10.12 execution-validation environment.
#
# Everything is installed under $CR_ROOT (default /opt/cleanroom), outside the repository.
# No sudo, no system Python, no shell-profile changes (Miniconda batch mode `-b`).
# Sources (only):
#   - Miniconda installer:  https://repo.anaconda.com/miniconda/   (SHA-256 published in its index)
#   - CPython + C libs:     https://repo.anaconda.com/pkgs/main    (Anaconda "defaults" main channel)
#   - pytest and deps:      https://pypi.org                       (hash-pinned wheels)
set -euo pipefail

CR_ROOT="${CR_ROOT:-/opt/cleanroom}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MINICONDA="Miniconda3-py310_23.5.2-0-Linux-x86_64.sh"
MINICONDA_SHA256="ea5e6e8a3d5a0247b9df85382d27220fac8e59b5778fd313c5913879cd9baafc"
CHANNEL="https://repo.anaconda.com/pkgs/main"
PYTHON_SPEC="python=3.10.12=h955ad1f_0"
PYTHON_PKG_SHA256="fdae369258833c513d334f9fde5fc84662f9d1be70fd69b0cb7644baf4f49652"  # python-3.10.12-h955ad1f_0.tar.bz2
ENV_PREFIX="$CR_ROOT/envs/py31012"

mkdir -p "$CR_ROOT/downloads"
export CONDARC="$CR_ROOT/condarc"          # ignore any user/system condarc
cat > "$CONDARC" <<EOF
channels: [$CHANNEL]
default_channels: [$CHANNEL]
channel_priority: strict
auto_update_conda: false
always_yes: true
use_only_tar_bz2: true
pkgs_dirs: [$CR_ROOT/pkgs]
envs_dirs: [$CR_ROOT/envs]
EOF

# 1. Miniconda installer, verified against the published SHA-256.
inst="$CR_ROOT/downloads/$MINICONDA"
[ -f "$inst" ] || curl -fsSL -o "$inst" "https://repo.anaconda.com/miniconda/$MINICONDA"
echo "$MINICONDA_SHA256  $inst" | sha256sum -c -

# 2. Base installation (used only to run conda; never used for experiments).
[ -x "$CR_ROOT/miniconda3/bin/conda" ] || bash "$inst" -b -p "$CR_ROOT/miniconda3"
CONDA="$CR_ROOT/miniconda3/bin/conda"

# 3. Experiment environment: exact CPython build from the main channel.
if [ ! -x "$ENV_PREFIX/bin/python" ]; then
  if [ -f "$HERE/conda-explicit.lock.txt" ]; then
    "$CONDA" create -p "$ENV_PREFIX" --override-channels -c "$CHANNEL" --file "$HERE/conda-explicit.lock.txt"
  else
    "$CONDA" create -p "$ENV_PREFIX" --override-channels -c "$CHANNEL" \
      "$PYTHON_SPEC" "pip=23.2.1" "setuptools=68.0.0" "wheel=0.41.2"
  fi
fi
echo "$PYTHON_PKG_SHA256  $CR_ROOT/pkgs/python-3.10.12-h955ad1f_0.tar.bz2" | sha256sum -c -

# 4. pytest stack from PyPI, hash-checked, no dependency resolution, wheels only.
PIP_CONFIG_FILE=/dev/null "$ENV_PREFIX/bin/python" -I -m pip install --isolated --no-cache-dir \
  --no-deps --require-hashes --only-binary=:all: -r "$HERE/requirements-validation.txt"

# 5. Record what was installed.
"$CONDA" list -p "$ENV_PREFIX" --explicit --sha256 > "$HERE/conda-explicit.lock.txt"
"$ENV_PREFIX/bin/python" -I -m pip freeze --all > "$HERE/pip-freeze.lock.txt"
"$ENV_PREFIX/bin/python" -I -m pip check
"$ENV_PREFIX/bin/python" -I -c 'import sys; assert sys.version_info[:3] == (3, 10, 12), sys.version; print(sys.version)'
"$ENV_PREFIX/bin/python" -I -m pytest --version
echo "environment ready: $ENV_PREFIX"
