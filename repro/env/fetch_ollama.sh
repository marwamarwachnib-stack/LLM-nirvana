#!/usr/bin/env bash
# Install a pinned Ollama build (CPU runner) from the official ollama/ollama image on Docker Hub.
# The ROCm variant is used only because its layer is smaller (1.2 GB vs 3.4 GB); GPU libraries are not extracted.
set -euo pipefail
REPRO_HOME="${REPRO_HOME:-/opt/repro}"
OLLAMA_TAG="0.40.3-rocm"
IMAGE_DIGEST="sha256:85ae816a67abeeaad8b9cc7d0fff5a4f0b1674a9d4ccc4a873d3c493ceea154f"   # linux/amd64 manifest of 0.40.3-rocm
BIN_LAYER="sha256:1e24cf30bb318d237bfcb7b9a63e963420ccbd0287b67b43a7e67dc161c51a4c"   # layer holding /usr/bin/ollama
LIB_LAYER="sha256:6a7bb5da961fa17120f7ff2ae26c190def7ea74a1248b365dd975600e7e532c6"   # layer holding /usr/lib/ollama
source "$(dirname "$0")/dockerhub.sh"
mkdir -p "$REPRO_HOME/ollama"
if [ ! -x "$REPRO_HOME/ollama/bin/ollama" ]; then
  dh_blob ollama/ollama "$BIN_LAYER" "$REPRO_HOME/ollama/bin.tar.gz"
  tar -xzf "$REPRO_HOME/ollama/bin.tar.gz" -C "$REPRO_HOME/ollama" --strip-components=1 usr/bin/ollama
  dh_blob ollama/ollama "$LIB_LAYER" "$REPRO_HOME/ollama/lib.tar.gz"
  tar -xzf "$REPRO_HOME/ollama/lib.tar.gz" -C "$REPRO_HOME/ollama" --strip-components=1 \
      --exclude='usr/lib/ollama/rocm*' usr/lib/ollama
  rm "$REPRO_HOME/ollama/bin.tar.gz" "$REPRO_HOME/ollama/lib.tar.gz"
fi
"$REPRO_HOME/ollama/bin/ollama" --version || true
echo "ollama image ollama/ollama:$OLLAMA_TAG@$IMAGE_DIGEST"
