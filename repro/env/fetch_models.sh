#!/usr/bin/env bash
# Download GGUF weights (pinned by sha256) from Docker Hub's ai/ namespace and register them in Ollama.
# Usage: fetch_models.sh [model-key ...]   (default: all keys in models.tsv)
set -euo pipefail
REPRO_HOME="${REPRO_HOME:-/opt/repro}"
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/dockerhub.sh"
export OLLAMA_MODELS="$REPRO_HOME/ollama/models"
"$HERE/ollama_serve.sh" >/dev/null
mkdir -p "$REPRO_HOME/gguf" "$OLLAMA_MODELS"
keys=("$@")
while IFS=$'\t' read -r key repo tag digest file; do
  [[ "$key" == \#* || -z "$key" ]] && continue
  if [ ${#keys[@]} -gt 0 ] && [[ ! " ${keys[*]} " =~ " $key " ]]; then continue; fi
  out="$REPRO_HOME/gguf/$file"
  [ -f "$out" ] || dh_blob "$repo" "$digest" "$out"
  printf 'FROM %s\n' "$out" > "$REPRO_HOME/gguf/$key.Modelfile"
  "$REPRO_HOME/ollama/bin/ollama" create "$key" -f "$REPRO_HOME/gguf/$key.Modelfile"
done < "$HERE/models.tsv"
